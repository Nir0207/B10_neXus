from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg.rows import dict_row

from .deidentify import deidentify_text
from .models import GeneRecord, OpenTargetsEvidence, PathwayRecord, StudyPathwayContext, StudySnippet

_CREATE_STUDIES_TABLE = """
CREATE TABLE IF NOT EXISTS silver.ncbi_studies (
    uid BIGINT PRIMARY KEY,
    accession TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    deidentified_summary TEXT NOT NULL,
    publication_date TEXT,
    sample_count INTEGER,
    platform TEXT,
    data_source TEXT NOT NULL DEFAULT 'NCBI GEO'
);
"""

_CREATE_STUDIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ncbi_studies_accession
ON silver.ncbi_studies (accession);
"""

_UPSERT_STUDY = """
INSERT INTO silver.ncbi_studies
    (uid, accession, title, deidentified_summary, publication_date, sample_count, platform, data_source)
VALUES
    (%(uid)s, %(accession)s, %(title)s, %(deidentified_summary)s, %(publication_date)s, %(sample_count)s, %(platform)s, %(data_source)s)
ON CONFLICT (uid) DO UPDATE
SET accession = EXCLUDED.accession,
    title = EXCLUDED.title,
    deidentified_summary = EXCLUDED.deidentified_summary,
    publication_date = EXCLUDED.publication_date,
    sample_count = EXCLUDED.sample_count,
    platform = EXCLUDED.platform,
    data_source = EXCLUDED.data_source;
"""


class PostgresStudyRepository:
    """Read/write access to staging study and pathway context."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def ensure_studies_table(self) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_STUDIES_TABLE)
                cur.execute(_CREATE_STUDIES_INDEX)

    def seed_studies_from_csv(self, csv_path: Path) -> int:
        if not csv_path.exists():
            return 0

        rows = list(self._iter_seed_rows(csv_path))
        if not rows:
            return 0

        with psycopg.connect(self._dsn, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.executemany(_UPSERT_STUDY, rows)
            conn.commit()

        return len(rows)

    def resolve_gene(self, gene_or_uniprot: str) -> GeneRecord | None:
        normalized = gene_or_uniprot.strip().upper()
        if not normalized:
            return None

        query = """
        SELECT
            uniprot_accession,
            COALESCE(NULLIF(gene_name, ''), %s) AS gene_name
        FROM silver.proteins
        WHERE UPPER(uniprot_accession) = %s OR UPPER(gene_name) = %s
        ORDER BY CASE WHEN UPPER(gene_name) = %s THEN 0 ELSE 1 END
        LIMIT 1;
        """
        try:
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (normalized, normalized, normalized, normalized))
                    row = cur.fetchone()
        except psycopg.Error:
            return None

        if not row:
            return None

        return GeneRecord(gene_symbol=str(row["gene_name"]), uniprot_id=str(row["uniprot_accession"]))

    def fetch_pathways_for_uniprot(self, uniprot_id: str, *, limit: int) -> list[PathwayRecord]:
        query = """
        SELECT DISTINCT
            pp.uniprot_id,
            pp.reactome_id,
            COALESCE(pw.pathway_name, 'Unknown pathway') AS pathway_name
        FROM silver.protein_pathway pp
        LEFT JOIN silver.pathways pw ON pw.reactome_id = pp.reactome_id
        WHERE pp.uniprot_id = %s
        ORDER BY pp.reactome_id
        LIMIT %s;
        """
        try:
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (uniprot_id, limit))
                    rows = cur.fetchall()
        except psycopg.Error:
            return []

        return [
            PathwayRecord(
                uniprot_id=str(row["uniprot_id"]),
                reactome_id=str(row["reactome_id"]),
                pathway_name=str(row["pathway_name"]),
            )
            for row in rows
        ]

    def fetch_study_snippets(self, query: str, *, limit: int) -> list[StudySnippet]:
        search_term = f"%{query.strip()}%"
        sql = """
        SELECT
            accession,
            title,
            LEFT(deidentified_summary, 1200) AS snippet,
            COALESCE(publication_date, '') AS publication_date
        FROM silver.ncbi_studies
        WHERE accession ILIKE %s OR title ILIKE %s OR deidentified_summary ILIKE %s
        ORDER BY publication_date DESC
        LIMIT %s;
        """

        try:
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (search_term, search_term, search_term, limit))
                    rows = cur.fetchall()
        except psycopg.Error:
            return []

        return [
            StudySnippet(
                accession=str(row["accession"]),
                title=str(row["title"]),
                snippet=str(row["snippet"]),
                publication_date=str(row["publication_date"]),
            )
            for row in rows
        ]

    def fetch_study_pathway_context(self, study_id: str, *, limit: int) -> StudyPathwayContext | None:
        study_query = """
        SELECT
            accession,
            title,
            LEFT(deidentified_summary, 1200) AS snippet,
            COALESCE(publication_date, '') AS publication_date
        FROM silver.ncbi_studies
        WHERE UPPER(accession) = UPPER(%s)
        LIMIT 1;
        """

        pathway_query = """
        SELECT DISTINCT
            p.uniprot_accession AS uniprot_id,
            pp.reactome_id,
            COALESCE(pw.pathway_name, 'Unknown pathway') AS pathway_name
        FROM silver.proteins p
        JOIN silver.protein_pathway pp ON pp.uniprot_id = p.uniprot_accession
        LEFT JOIN silver.pathways pw ON pw.reactome_id = pp.reactome_id
        WHERE p.gene_name IS NOT NULL
          AND POSITION(LOWER(p.gene_name) IN LOWER(%s)) > 0
        LIMIT %s;
        """

        try:
            with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(study_query, (study_id,))
                    study_row = cur.fetchone()
                    if not study_row:
                        return None

                    context_text = f"{study_row['title']} {study_row['snippet']}"
                    cur.execute(pathway_query, (context_text, limit))
                    pathway_rows = cur.fetchall()
        except psycopg.Error:
            return None

        study = StudySnippet(
            accession=str(study_row["accession"]),
            title=str(study_row["title"]),
            snippet=str(study_row["snippet"]),
            publication_date=str(study_row["publication_date"]),
        )
        pathways = [
            PathwayRecord(
                uniprot_id=str(row["uniprot_id"]),
                reactome_id=str(row["reactome_id"]),
                pathway_name=str(row["pathway_name"]),
            )
            for row in pathway_rows
        ]

        return StudyPathwayContext(study=study, related_pathways=pathways)

    def _iter_seed_rows(self, csv_path: Path) -> Iterable[dict[str, Any]]:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                uid = _safe_int(row.get("uid", ""))
                accession = (row.get("accession") or "").strip()
                title = (row.get("title") or "").strip()

                if uid is None or not accession or not title:
                    continue

                summary = deidentify_text((row.get("summary") or "").strip())
                sample_count = _safe_int(row.get("sample_count", ""))

                yield {
                    "uid": uid,
                    "accession": accession,
                    "title": title,
                    "deidentified_summary": summary,
                    "publication_date": (row.get("publication_date") or "").strip(),
                    "sample_count": sample_count,
                    "platform": (row.get("platform") or "").strip(),
                    "data_source": "NCBI GEO",
                }


class JsonOpenTargetsRepository:
    """Read Open Targets evidence snapshots from local JSON."""

    def __init__(self, evidence_path: Path):
        self._evidence_path = evidence_path

    def find_evidence_for_gene(self, gene_symbol: str, *, limit: int) -> list[OpenTargetsEvidence]:
        if not self._evidence_path.exists():
            return []

        import json

        payload = json.loads(self._evidence_path.read_text(encoding="utf-8"))
        disease = payload.get("data", {}).get("disease")
        if not disease:
            return []

        disease_name = str(disease.get("name") or "Unknown disease")
        rows = disease.get("associatedTargets", {}).get("rows", [])
        target = gene_symbol.strip().upper()
        evidence: list[OpenTargetsEvidence] = []

        for row in rows:
            target_info = row.get("target") or {}
            symbol = str(target_info.get("approvedSymbol") or "").upper()
            if symbol != target:
                continue

            score = float(row.get("score") or 0.0)
            evidence.append(
                OpenTargetsEvidence(
                    target_symbol=symbol,
                    disease_name=disease_name,
                    evidence_score=score,
                )
            )

        evidence.sort(key=lambda item: item.evidence_score, reverse=True)
        return evidence[:limit]


def _safe_int(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
