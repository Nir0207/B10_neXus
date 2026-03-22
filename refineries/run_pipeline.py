"""
BioNexus Refinery pipeline orchestrator.

Execution order
---------------
1. refine_uniprot  – raw UniProt JSON → Silver CSVs
2. refine_ncbi     – raw NCBI GEO JSON → Silver CSV
3. load_postgres   – upsert Silver CSVs into Postgres
4. trend_engine    – build disease intelligence aggregates in Postgres
5. load_neo4j      – merge Silver CSVs into Neo4j

Each step is idempotent by default (--force re-processes all files).
DB steps can be skipped with --skip-postgres / --skip-neo4j for local
CSV-only runs.

Usage
-----
    python run_pipeline.py
    python run_pipeline.py --force --skip-neo4j
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.ops_logger import configure_logging

configure_logging(service_name="refineries")
logger = logging.getLogger("pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="BioNexus Refinery Pipeline")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process files even if already in the idempotency manifest.",
    )
    parser.add_argument("--skip-postgres", action="store_true")
    parser.add_argument("--skip-neo4j", action="store_true")
    args = parser.parse_args()

    skip_processed = not args.force

    # ── Step 1: Refine UniProt ────────────────────────────────────────────────
    logger.info("=== Step 1/5  Refine UniProt JSON ===")
    from refine_uniprot import refine_uniprot

    proteins_df, gene_map_df, reactome_df = refine_uniprot(
        skip_processed=skip_processed
    )
    logger.info(
        "proteins=%d  gene_map=%d  pathways=%d",
        len(proteins_df),
        len(gene_map_df),
        len(reactome_df),
    )

    # ── Step 2: Refine NCBI ───────────────────────────────────────────────────
    logger.info("=== Step 2/5  Refine NCBI GEO JSON ===")
    from refine_ncbi import refine_ncbi

    studies_df = refine_ncbi(skip_processed=skip_processed)
    logger.info("studies=%d", len(studies_df))

    # ── Step 3: Load Postgres ─────────────────────────────────────────────────
    if not args.skip_postgres:
        logger.info("=== Step 3/5  Load Postgres ===")
        try:
            from load_postgres import run as pg_run

            pg_run()
        except Exception as exc:
            logger.error("Postgres load failed: %s", exc)
            sys.exit(1)

        logger.info("=== Step 4/5  Build disease intelligence ===")
        try:
            from trend_engine import run as trend_run

            trend_rows = trend_run()
            logger.info("disease_intelligence=%d", trend_rows)
        except Exception as exc:
            logger.error("Trend engine failed: %s", exc)
            sys.exit(1)
    else:
        logger.info("Skipping Postgres load and trend engine (--skip-postgres).")

    # ── Step 5/5: Load Neo4j ─────────────────────────────────────────────────
    if not args.skip_neo4j:
        logger.info("=== Step 5/5  Load Neo4j ===")
        try:
            from load_neo4j import run as neo4j_run

            neo4j_run()
        except Exception as exc:
            logger.error("Neo4j load failed: %s", exc)
            sys.exit(1)
    else:
        logger.info("Skipping Neo4j load (--skip-neo4j).")

    logger.info("=== Pipeline complete. ===")


if __name__ == "__main__":
    main()
