"""
Postgres Silver-layer loader.

Upserts refined CSV data into the silver schema.  All writes are wrapped
in a single transaction; the caller provides the connection so that
run() can be unit-tested with a mock.

Schema additions (pathways + protein_pathway junction) are created
idempotently via CREATE TABLE IF NOT EXISTS before any DML.
"""
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
import psycopg

from config import PG_DSN, SILVER_CSV_DIR

logger = logging.getLogger(__name__)

# ── DDL ───────────────────────────────────────────────────────────────────────

_CREATE_PATHWAYS = """
CREATE TABLE IF NOT EXISTS silver.pathways (
    reactome_id  VARCHAR(20) PRIMARY KEY,
    pathway_name TEXT        NOT NULL,
    created_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_PROTEIN_PATHWAY = """
CREATE TABLE IF NOT EXISTS silver.protein_pathway (
    uniprot_id  VARCHAR(10) NOT NULL,
    reactome_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (uniprot_id, reactome_id)
);
"""

# ── DML ───────────────────────────────────────────────────────────────────────

_UPSERT_PROTEIN = """
INSERT INTO silver.proteins
    (uniprot_accession, gene_name, protein_name, organism, sequence, molecular_weight)
VALUES
    (%(uniprot_id)s, %(hgnc_symbol)s, %(protein_name)s,
     %(organism)s,  %(sequence)s,    %(molecular_weight)s)
ON CONFLICT (uniprot_accession) DO UPDATE SET
    gene_name        = EXCLUDED.gene_name,
    protein_name     = EXCLUDED.protein_name,
    organism         = EXCLUDED.organism,
    sequence         = EXCLUDED.sequence,
    molecular_weight = EXCLUDED.molecular_weight,
    updated_at       = CURRENT_TIMESTAMP;
"""

_UPSERT_GENE = """
INSERT INTO silver.genes (hgnc_symbol)
VALUES (%(hgnc_symbol)s)
ON CONFLICT (hgnc_symbol) DO NOTHING;
"""

_UPSERT_PATHWAY = """
INSERT INTO silver.pathways (reactome_id, pathway_name)
VALUES (%(reactome_id)s, %(pathway_name)s)
ON CONFLICT (reactome_id) DO UPDATE SET
    pathway_name = EXCLUDED.pathway_name;
"""

_UPSERT_PROTEIN_PATHWAY = """
INSERT INTO silver.protein_pathway (uniprot_id, reactome_id)
VALUES (%(uniprot_id)s, %(reactome_id)s)
ON CONFLICT DO NOTHING;
"""


# ── Loader functions (accept connection for testability) ─────────────────────

def load_proteins(
    conn: psycopg.Connection,
    csv_path: Path = SILVER_CSV_DIR / "silver_proteins.csv",
) -> int:
    df = pl.read_csv(csv_path, null_values=[""])
    rows = df.select(
        ["uniprot_id", "hgnc_symbol", "protein_name", "organism", "sequence", "molecular_weight"]
    ).to_dicts()
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_PROTEIN, rows)
    logger.info("Upserted %d protein rows", len(rows))
    return len(rows)


def load_genes(
    conn: psycopg.Connection,
    csv_path: Path = SILVER_CSV_DIR / "silver_gene_symbol_map.csv",
) -> int:
    df = pl.read_csv(csv_path, null_values=[""])
    rows = [
        {"hgnc_symbol": s}
        for s in df["gene_symbol"].unique().to_list()
        if s
    ]
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_GENE, rows)
    logger.info("Upserted %d gene rows", len(rows))
    return len(rows)


def load_pathways(
    conn: psycopg.Connection,
    csv_path: Path = SILVER_CSV_DIR / "silver_reactome_map.csv",
) -> int:
    df = pl.read_csv(csv_path, null_values=[""])
    if df.is_empty():
        return 0

    pathway_rows = df.select(["reactome_id", "pathway_name"]).unique(
        subset=["reactome_id"]
    ).to_dicts()
    pp_rows = df.select(["uniprot_id", "reactome_id"]).unique().to_dicts()

    with conn.cursor() as cur:
        cur.execute(_CREATE_PATHWAYS)
        cur.execute(_CREATE_PROTEIN_PATHWAY)
        cur.executemany(_UPSERT_PATHWAY, pathway_rows)
        cur.executemany(_UPSERT_PROTEIN_PATHWAY, pp_rows)

    logger.info(
        "Upserted %d pathway rows and %d protein-pathway links",
        len(pathway_rows),
        len(pp_rows),
    )
    return len(pathway_rows) + len(pp_rows)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run(dsn: str = PG_DSN) -> None:
    with psycopg.connect(dsn, autocommit=False) as conn:
        try:
            load_proteins(conn)
            load_genes(conn)
            load_pathways(conn)
            conn.commit()
            logger.info("Postgres Silver load complete.")
        except Exception:
            conn.rollback()
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
