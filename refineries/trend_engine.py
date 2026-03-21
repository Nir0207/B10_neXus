"""
Historical disease trend aggregation for BioNexus.

Builds a disease_intelligence table in Postgres from the local lake using
Polars-centric transformations. Open Targets evidence is preferred for
gene ranking when present; UniProt disease annotations provide a local
fallback when the snapshot is incomplete.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import polars as pl
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from config import PG_DSN, RAW_ROOT_DIR, RAW_UNIPROT_DIR, SILVER_CSV_DIR

logger = logging.getLogger(__name__)

_CREATE_DISEASE_INTELLIGENCE = """
CREATE TABLE IF NOT EXISTS disease_intelligence (
    disease_id TEXT PRIMARY KEY,
    disease_name TEXT NOT NULL,
    frequency_timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    gene_distribution JSONB NOT NULL DEFAULT '[]'::jsonb,
    organ_affinity JSONB NOT NULL DEFAULT '[]'::jsonb,
    therapeutic_landscape JSONB NOT NULL DEFAULT '[]'::jsonb,
    clinical_summary TEXT NOT NULL DEFAULT '',
    top_gene_uniprot_ids TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_DISEASE_INTELLIGENCE_NAME_INDEX = """
CREATE INDEX IF NOT EXISTS idx_disease_intelligence_name_lower
ON disease_intelligence (LOWER(disease_name));
"""

_UPSERT_DISEASE_INTELLIGENCE = """
INSERT INTO disease_intelligence (
    disease_id,
    disease_name,
    frequency_timeline,
    gene_distribution,
    organ_affinity,
    therapeutic_landscape,
    clinical_summary,
    top_gene_uniprot_ids
)
VALUES (
    %(disease_id)s,
    %(disease_name)s,
    %(frequency_timeline)s,
    %(gene_distribution)s,
    %(organ_affinity)s,
    %(therapeutic_landscape)s,
    %(clinical_summary)s,
    %(top_gene_uniprot_ids)s
)
ON CONFLICT (disease_id) DO UPDATE SET
    disease_name = EXCLUDED.disease_name,
    frequency_timeline = EXCLUDED.frequency_timeline,
    gene_distribution = EXCLUDED.gene_distribution,
    organ_affinity = EXCLUDED.organ_affinity,
    therapeutic_landscape = EXCLUDED.therapeutic_landscape,
    clinical_summary = EXCLUDED.clinical_summary,
    top_gene_uniprot_ids = EXCLUDED.top_gene_uniprot_ids,
    updated_at = CURRENT_TIMESTAMP;
"""

_THERAPEUTIC_LANDSCAPE_QUERY = """
SELECT
    mgb.chembl_id,
    COALESCE(mc.name, mgb.chembl_id) AS molecule_name,
    mgb.uniprot_id,
    COALESCE(g.hgnc_symbol, mgb.uniprot_id) AS gene_symbol,
    mgb.affinity
FROM medicine_gene_bindings AS mgb
LEFT JOIN medicine_catalog AS mc
    ON mc.chembl_id = mgb.chembl_id
LEFT JOIN silver.genes AS g
    ON g.uniprot_id = mgb.uniprot_id
WHERE mgb.uniprot_id = ANY(%s)
ORDER BY mgb.affinity NULLS LAST, mgb.chembl_id, mgb.uniprot_id;
"""
_THERAPEUTIC_TABLES_EXIST_QUERY = """
SELECT
    to_regclass('public.medicine_gene_bindings') IS NOT NULL
    AND to_regclass('public.medicine_catalog') IS NOT NULL
    AND to_regclass('silver.genes') IS NOT NULL
"""

_TISSUE_PATTERNS: dict[str, tuple[str, ...]] = {
    "brain": ("brain", "neural", "cerebral", "neuronal"),
    "breast": ("breast",),
    "heart": ("heart", "cardiac"),
    "kidney": ("kidney", "renal", "nephro"),
    "liver": ("liver", "hepatic"),
    "lung": ("lung", "pulmonary"),
    "ovary": ("ovar",),
    "pancreas": ("pancrea",),
    "skin": ("skin", "cutaneous"),
    "systemic": ("ubiquitous", "widely expressed", "widely"),
}


def _canonical_disease_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value)
    if match is None:
        return None
    return int(match.group(0))


def _slug_or_none(value: str) -> str | None:
    slug = _canonical_disease_id(value)
    return slug or None


def _extract_tissue_labels(text: str) -> list[str]:
    normalized = text.strip().lower()
    if not normalized:
        return []

    labels = [
        label
        for label, patterns in _TISSUE_PATTERNS.items()
        if any(pattern in normalized for pattern in patterns)
    ]
    if labels:
        return labels
    return ["unspecified"]


def _load_gene_lookup(proteins_csv_path: Path) -> pl.DataFrame:
    proteins_df = pl.read_csv(proteins_csv_path, null_values=[""])
    prioritized_df = proteins_df.with_columns(
        pl.when(pl.col("organism").str.contains("Homo sapiens", literal=True))
        .then(pl.lit(0))
        .otherwise(pl.lit(1))
        .alias("organism_rank"),
        pl.col("hgnc_symbol").str.to_uppercase().alias("gene_symbol"),
    )

    return (
        prioritized_df
        .filter(pl.col("gene_symbol").str.strip_chars() != "")
        .sort(["gene_symbol", "organism_rank", "uniprot_id"])
        .unique(subset=["gene_symbol"], keep="first")
        .select(["gene_symbol", "uniprot_id"])
    )


def _load_studies(studies_csv_path: Path) -> pl.DataFrame:
    studies_df = pl.read_csv(studies_csv_path, null_values=[""])
    return studies_df.with_columns(
        pl.col("gene_symbol").str.to_uppercase().alias("gene_symbol"),
        pl.col("title").fill_null("").alias("title"),
        pl.col("summary").fill_null("").alias("summary"),
        pl.col("publication_date")
        .fill_null("")
        .map_elements(_safe_year, return_dtype=pl.Int64)
        .alias("year"),
    )


def _iter_human_uniprot_entries(raw_uniprot_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_uniprot_dir.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload.get("results", []):
            organism = str(entry.get("organism", {}).get("scientificName") or "").strip()
            if organism != "Homo sapiens":
                continue
            rows.append(entry)
    return rows


def _load_uniprot_context(raw_uniprot_dir: Path) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    association_rows: list[dict[str, Any]] = []
    tissue_rows: list[dict[str, Any]] = []
    chembl_rows: list[dict[str, Any]] = []

    for entry in _iter_human_uniprot_entries(raw_uniprot_dir):
        genes = entry.get("genes") or []
        first_gene = genes[0] if genes else {}
        gene_symbol = str(first_gene.get("geneName", {}).get("value") or "").strip().upper()
        uniprot_id = str(entry.get("primaryAccession") or "").strip().upper()
        if not gene_symbol or not uniprot_id:
            continue

        for comment in entry.get("comments", []):
            comment_type = str(comment.get("commentType") or "").upper()
            if comment_type == "DISEASE":
                disease = comment.get("disease") or {}
                disease_name = str(disease.get("diseaseId") or "").strip()
                if not disease_name:
                    continue

                evidences = disease.get("evidences") or []
                association_rows.append(
                    {
                        "disease_id": _canonical_disease_id(disease_name),
                        "disease_name": disease_name,
                        "uniprot_id": uniprot_id,
                        "gene_symbol": gene_symbol,
                        "association_score": max(0.2, min(1.0, len(evidences) * 0.2)),
                        "association_source": "UniProt",
                    }
                )
            elif comment_type == "TISSUE SPECIFICITY":
                for text in comment.get("texts", []):
                    value = str(text.get("value") or "").strip()
                    if not value:
                        continue
                    tissue_rows.append(
                        {
                            "uniprot_id": uniprot_id,
                            "gene_symbol": gene_symbol,
                            "tissue_specificity": value,
                        }
                    )

        for xref in entry.get("uniProtKBCrossReferences", []):
            if xref.get("database") != "ChEMBL":
                continue
            chembl_id = str(xref.get("id") or "").strip().upper()
            if not chembl_id:
                continue
            chembl_rows.append(
                {
                    "chembl_id": chembl_id,
                    "uniprot_id": uniprot_id,
                    "gene_symbol": gene_symbol,
                }
            )

    associations_df = (
        pl.DataFrame(association_rows)
        if association_rows
        else pl.DataFrame(
            schema={
                "disease_id": pl.Utf8,
                "disease_name": pl.Utf8,
                "uniprot_id": pl.Utf8,
                "gene_symbol": pl.Utf8,
                "association_score": pl.Float64,
                "association_source": pl.Utf8,
            }
        )
    )
    tissues_df = (
        pl.DataFrame(tissue_rows)
        if tissue_rows
        else pl.DataFrame(
            schema={
                "uniprot_id": pl.Utf8,
                "gene_symbol": pl.Utf8,
                "tissue_specificity": pl.Utf8,
            }
        )
    )
    chembl_df = (
        pl.DataFrame(chembl_rows)
        if chembl_rows
        else pl.DataFrame(
            schema={
                "chembl_id": pl.Utf8,
                "uniprot_id": pl.Utf8,
                "gene_symbol": pl.Utf8,
            }
        )
    )

    return associations_df, tissues_df, chembl_df


def _load_open_targets_context(raw_opentargets_dir: Path, gene_lookup_df: pl.DataFrame) -> pl.DataFrame:
    symbol_lookup = {
        str(row["gene_symbol"]).upper(): str(row["uniprot_id"]).upper()
        for row in gene_lookup_df.to_dicts()
    }
    association_rows: list[dict[str, Any]] = []

    for path in sorted(raw_opentargets_dir.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        disease = payload.get("data", {}).get("disease")
        if not isinstance(disease, dict):
            continue

        disease_name = str(disease.get("name") or "").strip()
        if not disease_name:
            continue
        disease_id = _slug_or_none(str(disease.get("id") or disease_name))
        if disease_id is None:
            continue

        for row in disease.get("associatedTargets", {}).get("rows", []):
            target = row.get("target") or {}
            gene_symbol = str(target.get("approvedSymbol") or "").strip().upper()
            if not gene_symbol:
                continue

            protein_ids = target.get("proteinIds") or []
            uniprot_id = next(
                (
                    str(candidate).strip().upper()
                    for candidate in protein_ids
                    if isinstance(candidate, str) and candidate.strip()
                ),
                symbol_lookup.get(gene_symbol),
            )
            if not uniprot_id:
                continue

            association_rows.append(
                {
                    "disease_id": disease_id,
                    "disease_name": disease_name,
                    "uniprot_id": uniprot_id,
                    "gene_symbol": gene_symbol,
                    "association_score": _safe_float(row.get("score")),
                    "association_source": "Open Targets",
                }
            )

    if not association_rows:
        return pl.DataFrame(
            schema={
                "disease_id": pl.Utf8,
                "disease_name": pl.Utf8,
                "uniprot_id": pl.Utf8,
                "gene_symbol": pl.Utf8,
                "association_score": pl.Float64,
                "association_source": pl.Utf8,
            }
        )

    return pl.DataFrame(association_rows)


def _resolve_associations(
    open_targets_df: pl.DataFrame,
    uniprot_df: pl.DataFrame,
) -> pl.DataFrame:
    combined = pl.concat([open_targets_df, uniprot_df], how="diagonal_relaxed")
    if combined.is_empty():
        return combined

    return (
        combined
        .with_columns(
            pl.when(pl.col("association_source") == "Open Targets")
            .then(pl.lit(0))
            .otherwise(pl.lit(1))
            .alias("source_rank")
        )
        .sort(["disease_id", "source_rank", "association_score"], descending=[False, False, True])
        .unique(subset=["disease_id", "uniprot_id"], keep="first")
        .drop("source_rank")
    )


def _build_frequency_timeline(
    disease_name: str,
    top_gene_symbols: list[str],
    studies_df: pl.DataFrame,
) -> list[dict[str, Any]]:
    if studies_df.is_empty():
        return []

    disease_pattern = re.escape(disease_name.strip())
    if disease_pattern:
        disease_mask = (
            pl.col("title").str.contains(disease_pattern, literal=False, strict=False)
            | pl.col("summary").str.contains(disease_pattern, literal=False, strict=False)
        )
    else:
        disease_mask = pl.lit(False)

    gene_mask = pl.col("gene_symbol").is_in(top_gene_symbols) if top_gene_symbols else pl.lit(False)
    timeline_df = (
        studies_df
        .filter((gene_mask | disease_mask) & pl.col("year").is_not_null())
        .group_by("year")
        .agg(pl.col("accession").n_unique().alias("study_count"))
        .sort("year")
    )
    return timeline_df.to_dicts()


def _build_organ_affinity(
    top_gene_ids: list[str],
    tissues_df: pl.DataFrame,
) -> list[dict[str, Any]]:
    if not top_gene_ids or tissues_df.is_empty():
        return []

    rows = tissues_df.filter(pl.col("uniprot_id").is_in(top_gene_ids)).to_dicts()
    tissue_counts: dict[str, int] = {}
    for row in rows:
        for label in _extract_tissue_labels(str(row["tissue_specificity"])):
            tissue_counts[label] = tissue_counts.get(label, 0) + 1

    return [
        {"organ": label.title(), "value": count}
        for label, count in sorted(tissue_counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _fetch_bound_molecules(
    conn: psycopg.Connection[Any],
    top_gene_ids: list[str],
) -> list[dict[str, Any]]:
    if not top_gene_ids:
        return []

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_THERAPEUTIC_TABLES_EXIST_QUERY)
            exists_row = cur.fetchone()
            if not exists_row or list(exists_row.values())[0] is not True:
                return []
            cur.execute(_THERAPEUTIC_LANDSCAPE_QUERY, (top_gene_ids,))
            rows = cur.fetchall()
    except psycopg.Error:
        return []

    return [
        {
            "chembl_id": str(row["chembl_id"]),
            "molecule_name": str(row["molecule_name"]),
            "uniprot_id": str(row["uniprot_id"]),
            "gene_symbol": str(row["gene_symbol"]),
            "bioactivity_status": "Active",
            "evidence_source": "Postgres medicine_gene_bindings",
            "affinity": _safe_float(row["affinity"]),
        }
        for row in rows
    ]


def _build_therapeutic_landscape(
    conn: psycopg.Connection[Any],
    top_gene_ids: list[str],
    chembl_df: pl.DataFrame,
) -> list[dict[str, Any]]:
    bound_molecules = _fetch_bound_molecules(conn, top_gene_ids)
    if bound_molecules:
        return bound_molecules

    if not top_gene_ids or chembl_df.is_empty():
        return []

    return [
        {
            "chembl_id": row["chembl_id"],
            "molecule_name": row["chembl_id"],
            "uniprot_id": row["uniprot_id"],
            "gene_symbol": row["gene_symbol"],
            "bioactivity_status": "Cross-referenced",
            "evidence_source": "UniProt ChEMBL cross-reference",
        }
        for row in (
            chembl_df
            .filter(pl.col("uniprot_id").is_in(top_gene_ids))
            .unique(subset=["chembl_id", "uniprot_id"])
            .sort(["chembl_id", "uniprot_id"])
            .to_dicts()
        )
    ]


def _build_clinical_summary(
    disease_name: str,
    frequency_timeline: list[dict[str, Any]],
    gene_distribution: list[dict[str, Any]],
    organ_affinity: list[dict[str, Any]],
    therapeutic_landscape: list[dict[str, Any]],
) -> str:
    total_studies = sum(int(item["study_count"]) for item in frequency_timeline)
    years = [int(item["year"]) for item in frequency_timeline if item.get("year") is not None]
    if years:
        timeline_text = f"{total_studies} unique study snapshots from {min(years)} to {max(years)}"
    else:
        timeline_text = "no staged study timeline yet"

    if gene_distribution:
        lead_gene = gene_distribution[0]
        gene_text = (
            f"Top target signal centers on {lead_gene['gene_symbol']} "
            f"(UniProt {lead_gene['uniprot_id']}, score {lead_gene['association_score']:.2f})"
        )
    else:
        gene_text = "target ranking is currently unavailable"

    if organ_affinity:
        affinity_text = f"dominant tissue affinity is {organ_affinity[0]['organ']}"
    else:
        affinity_text = "tissue affinity is unresolved"

    landscape_text = (
        f"{len(therapeutic_landscape)} linked ChEMBL molecules are available"
        if therapeutic_landscape
        else "no linked ChEMBL molecules were found in staging"
    )

    return f"{disease_name}: {timeline_text}. {gene_text}. {affinity_text}. {landscape_text}."


def build_disease_records(
    *,
    raw_uniprot_dir: Path = RAW_UNIPROT_DIR,
    raw_opentargets_dir: Path = RAW_ROOT_DIR / "opentargets",
    studies_csv_path: Path = SILVER_CSV_DIR / "silver_ncbi_studies.csv",
    proteins_csv_path: Path = SILVER_CSV_DIR / "silver_proteins.csv",
    conn: psycopg.Connection[Any] | None = None,
) -> list[dict[str, Any]]:
    gene_lookup_df = _load_gene_lookup(proteins_csv_path)
    studies_df = _load_studies(studies_csv_path)
    uniprot_associations_df, tissues_df, chembl_df = _load_uniprot_context(raw_uniprot_dir)
    open_targets_df = _load_open_targets_context(raw_opentargets_dir, gene_lookup_df)
    associations_df = _resolve_associations(open_targets_df, uniprot_associations_df)

    if associations_df.is_empty():
        return []

    disease_rows = associations_df.select(["disease_id", "disease_name"]).unique().sort("disease_name").to_dicts()
    records: list[dict[str, Any]] = []

    for disease_row in disease_rows:
        disease_id = str(disease_row["disease_id"])
        disease_name = str(disease_row["disease_name"])
        top_genes_df = (
            associations_df
            .filter(pl.col("disease_id") == disease_id)
            .sort("association_score", descending=True)
            .head(10)
        )
        gene_distribution = [
            {
                "uniprot_id": row["uniprot_id"],
                "gene_symbol": row["gene_symbol"],
                "association_score": round(float(row["association_score"]), 4),
                "association_source": row["association_source"],
            }
            for row in top_genes_df.to_dicts()
        ]
        top_gene_symbols = [str(row["gene_symbol"]) for row in gene_distribution]
        top_gene_ids = [str(row["uniprot_id"]) for row in gene_distribution]
        frequency_timeline = _build_frequency_timeline(disease_name, top_gene_symbols, studies_df)
        organ_affinity = _build_organ_affinity(top_gene_ids, tissues_df)
        therapeutic_landscape = (
            _build_therapeutic_landscape(conn, top_gene_ids, chembl_df)
            if conn is not None
            else []
        )
        clinical_summary = _build_clinical_summary(
            disease_name=disease_name,
            frequency_timeline=frequency_timeline,
            gene_distribution=gene_distribution,
            organ_affinity=organ_affinity,
            therapeutic_landscape=therapeutic_landscape,
        )

        records.append(
            {
                "disease_id": disease_id,
                "disease_name": disease_name,
                "frequency_timeline": frequency_timeline,
                "gene_distribution": gene_distribution,
                "organ_affinity": organ_affinity,
                "therapeutic_landscape": therapeutic_landscape,
                "clinical_summary": clinical_summary,
                "top_gene_uniprot_ids": top_gene_ids,
            }
        )

    return records


def load_disease_intelligence(
    conn: psycopg.Connection[Any],
    records: list[dict[str, Any]],
) -> int:
    with conn.cursor() as cur:
        cur.execute(_CREATE_DISEASE_INTELLIGENCE)
        cur.execute(_CREATE_DISEASE_INTELLIGENCE_NAME_INDEX)
        if not records:
            return 0
        cur.executemany(
            _UPSERT_DISEASE_INTELLIGENCE,
            [
                {
                    **record,
                    "frequency_timeline": Jsonb(record["frequency_timeline"]),
                    "gene_distribution": Jsonb(record["gene_distribution"]),
                    "organ_affinity": Jsonb(record["organ_affinity"]),
                    "therapeutic_landscape": Jsonb(record["therapeutic_landscape"]),
                }
                for record in records
            ],
        )
    return len(records)


def run(
    *,
    dsn: str = PG_DSN,
    raw_uniprot_dir: Path = RAW_UNIPROT_DIR,
    raw_opentargets_dir: Path = RAW_ROOT_DIR / "opentargets",
    studies_csv_path: Path = SILVER_CSV_DIR / "silver_ncbi_studies.csv",
    proteins_csv_path: Path = SILVER_CSV_DIR / "silver_proteins.csv",
) -> int:
    with psycopg.connect(dsn, autocommit=False) as conn:
        records = build_disease_records(
            raw_uniprot_dir=raw_uniprot_dir,
            raw_opentargets_dir=raw_opentargets_dir,
            studies_csv_path=studies_csv_path,
            proteins_csv_path=proteins_csv_path,
            conn=conn,
        )
        loaded = load_disease_intelligence(conn, records)
        conn.commit()
    logger.info("Upserted %d disease intelligence rows", loaded)
    return loaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
