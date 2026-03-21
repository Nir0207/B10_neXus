"""
Polars refinery for NCBI GEO raw JSON  (Bronze → Silver).

Reads every *.json file in RAW_NCBI_DIR (esummary format), extracts
study-level fields, and writes:

    silver_ncbi_studies.csv – one row per GEO study (GSE)
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import polars as pl

from config import RAW_NCBI_DIR, SILVER_CSV_DIR
from idempotency import filter_unprocessed, mark_processed_many

logger = logging.getLogger(__name__)

STUDY_SCHEMA: dict[str, pl.DataType] = {
    "uid": pl.Utf8,
    "accession": pl.Utf8,
    "gene_symbol": pl.Utf8,
    "title": pl.Utf8,
    "summary": pl.Utf8,
    "taxon": pl.Utf8,
    "gds_type": pl.Utf8,
    "entry_type": pl.Utf8,
    "publication_date": pl.Utf8,
    "sample_count": pl.Int64,
    "platform": pl.Utf8,
    "source_file": pl.Utf8,
}


# ── Field extraction ──────────────────────────────────────────────────────────

def _deidentify_text(value: str) -> str:
    redacted = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", value)
    redacted = re.sub(r"\b(?:\+?\d[\d -]{7,}\d)\b", "[REDACTED_PHONE]", redacted)
    redacted = re.sub(r"\bNCT\d{8}\b", "[REDACTED_TRIAL_ID]", redacted)
    return redacted


def _extract_gene_symbol(filepath: Path) -> str:
    stem = filepath.stem
    if stem.endswith("_studies"):
        stem = stem[:-8]
    return stem.upper()


def _extract_study(uid: str, study: dict[str, Any], *, gene_symbol: str, source_file: str) -> dict[str, Any]:
    """Flatten one NCBI esummary result entry."""
    return {
        "uid": uid,
        "accession": study.get("accession", ""),
        "gene_symbol": gene_symbol,
        "title": _deidentify_text(study.get("title", "")),
        "summary": _deidentify_text(study.get("summary", "")),
        "taxon": study.get("taxon", ""),
        "gds_type": study.get("gdstype", ""),
        "entry_type": study.get("entrytype", ""),
        "publication_date": study.get("pdat", ""),
        "sample_count": len(study.get("samples", [])),
        "platform": study.get("gpl", ""),
        "source_file": source_file,
    }


# ── Public refinery entry point ───────────────────────────────────────────────

def refine_ncbi(
    raw_dir: Path = RAW_NCBI_DIR,
    out_dir: Path = SILVER_CSV_DIR,
    *,
    skip_processed: bool = True,
) -> pl.DataFrame:
    """
    Read raw NCBI GEO JSON → return studies_df.

    Side-effects
    ------------
    - Writes silver_ncbi_studies.csv to *out_dir*.
    - Updates the idempotency manifest for each processed file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    json_files = sorted(raw_dir.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {raw_dir}")

    to_process = filter_unprocessed(json_files) if skip_processed else json_files

    if skip_processed and not to_process:
        logger.info("All NCBI files already processed; loading existing CSV.")
        return pl.read_csv(out_dir / "silver_ncbi_studies.csv")
    if skip_processed:
        logger.info(
            "Detected %d/%d changed NCBI files; rebuilding full Silver snapshot.",
            len(to_process),
            len(json_files),
        )

    studies: list[dict[str, Any]] = []

    for filepath in json_files:
        logger.info("Refining %s", filepath.name)
        data: dict = json.loads(filepath.read_text(encoding="utf-8"))
        result: dict = data.get("result", {})
        uids: list[str] = result.get("uids", [])
        gene_symbol = _extract_gene_symbol(filepath)
        source_file = filepath.relative_to(raw_dir).as_posix()

        for uid in uids:
            if uid in result:
                studies.append(
                    _extract_study(
                        uid,
                        result[uid],
                        gene_symbol=gene_symbol,
                        source_file=source_file,
                    )
                )

    if not studies:
        raise ValueError("No study records extracted — check raw NCBI JSON format.")

    df = (
        pl.from_dicts(studies, schema=STUDY_SCHEMA)
        .unique(subset=["uid"], keep="last")
        .sort(["gene_symbol", "uid"])
    )
    df.write_csv(out_dir / "silver_ncbi_studies.csv")
    if skip_processed and to_process:
        mark_processed_many(to_process)
    logger.info("Wrote %d NCBI study rows", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = refine_ncbi(skip_processed=True)
    print(f"studies={len(df)}")
