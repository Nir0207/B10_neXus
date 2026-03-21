"""
Polars refinery for NCBI GEO raw JSON  (Bronze → Silver).

Reads every *.json file in RAW_NCBI_DIR (esummary format), extracts
study-level fields, and writes:

    silver_ncbi_studies.csv – one row per GEO study (GSE)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import polars as pl

from config import RAW_NCBI_DIR, SILVER_CSV_DIR
from idempotency import filter_unprocessed, mark_processed_many

logger = logging.getLogger(__name__)


# ── Field extraction ──────────────────────────────────────────────────────────

def _extract_study(uid: str, study: dict[str, Any]) -> dict[str, Any]:
    """Flatten one NCBI esummary result entry."""
    return {
        "uid": uid,
        "accession": study.get("accession", ""),
        "title": study.get("title", ""),
        "summary": study.get("summary", ""),
        "taxon": study.get("taxon", ""),
        "gds_type": study.get("gdstype", ""),
        "entry_type": study.get("entrytype", ""),
        "publication_date": study.get("pdat", ""),
        "sample_count": len(study.get("samples", [])),
        "platform": study.get("gpl", ""),
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
    json_files = sorted(raw_dir.glob("*.json"))
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

    studies: list[dict] = []

    for filepath in json_files:
        logger.info("Refining %s", filepath.name)
        data: dict = json.loads(filepath.read_text(encoding="utf-8"))
        result: dict = data.get("result", {})
        uids: list[str] = result.get("uids", [])

        for uid in uids:
            if uid in result:
                studies.append(_extract_study(uid, result[uid]))

    if not studies:
        raise ValueError("No study records extracted — check raw NCBI JSON format.")

    df = pl.DataFrame(studies)
    df.write_csv(out_dir / "silver_ncbi_studies.csv")
    if skip_processed and to_process:
        mark_processed_many(to_process)
    logger.info("Wrote %d NCBI study rows", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = refine_ncbi(skip_processed=True)
    print(f"studies={len(df)}")
