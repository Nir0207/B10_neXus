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

_CREATE_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS silver;
"""

_CREATE_GENES = """
CREATE TABLE IF NOT EXISTS silver.genes (
    uniprot_id    VARCHAR(15) PRIMARY KEY,
    hgnc_symbol   VARCHAR(64) NOT NULL,
    gene_synonyms TEXT        NOT NULL DEFAULT '',
    data_source   TEXT        NOT NULL DEFAULT 'UniProt',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_ALTER_GENES = (
    "ALTER TABLE silver.genes ADD COLUMN IF NOT EXISTS uniprot_id VARCHAR(15);",
    "ALTER TABLE silver.genes ADD COLUMN IF NOT EXISTS gene_synonyms TEXT NOT NULL DEFAULT '';",
    "ALTER TABLE silver.genes ADD COLUMN IF NOT EXISTS data_source TEXT NOT NULL DEFAULT 'UniProt';",
)

_CREATE_GENES_UNIPROT_UNIQUE = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_silver_genes_uniprot_id
ON silver.genes (uniprot_id);
"""

_DROP_LEGACY_GENE_SYMBOL_UNIQUE = (
    "ALTER TABLE silver.genes DROP CONSTRAINT IF EXISTS genes_hgnc_symbol_key;",
    "DROP INDEX IF EXISTS idx_hgnc;",
)

_CREATE_PROTEINS = """
CREATE TABLE IF NOT EXISTS silver.proteins (
    uniprot_accession VARCHAR(15) PRIMARY KEY,
    gene_name         VARCHAR(64) NOT NULL,
    protein_name      TEXT        NOT NULL,
    organism          TEXT        NOT NULL,
    sequence          TEXT        NOT NULL,
    sequence_length   INTEGER,
    molecular_weight  BIGINT,
    annotation_score  DOUBLE PRECISION,
    data_source       TEXT        NOT NULL DEFAULT 'UniProt',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_ALTER_PROTEINS = (
    "ALTER TABLE silver.proteins ADD COLUMN IF NOT EXISTS sequence_length INTEGER;",
    "ALTER TABLE silver.proteins ADD COLUMN IF NOT EXISTS annotation_score DOUBLE PRECISION;",
    "ALTER TABLE silver.proteins ADD COLUMN IF NOT EXISTS data_source TEXT NOT NULL DEFAULT 'UniProt';",
)

_CREATE_PATHWAYS = """
CREATE TABLE IF NOT EXISTS silver.pathways (
    reactome_id  VARCHAR(20) PRIMARY KEY,
    pathway_name TEXT        NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_PROTEIN_PATHWAY = """
CREATE TABLE IF NOT EXISTS silver.protein_pathway (
    uniprot_id  VARCHAR(10) NOT NULL,
    reactome_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (uniprot_id, reactome_id),
    FOREIGN KEY (uniprot_id) REFERENCES silver.genes (uniprot_id),
    FOREIGN KEY (reactome_id) REFERENCES silver.pathways (reactome_id)
);
"""

# ── DML ───────────────────────────────────────────────────────────────────────

_UPSERT_PROTEIN = """
INSERT INTO silver.proteins
    (
        uniprot_accession,
        gene_name,
        protein_name,
        organism,
        sequence,
        sequence_length,
        molecular_weight,
        annotation_score,
        data_source
    )
VALUES
    (
        %(uniprot_id)s,
        %(hgnc_symbol)s,
        %(protein_name)s,
        %(organism)s,
        %(sequence)s,
        %(sequence_length)s,
        %(molecular_weight)s,
        %(annotation_score)s,
        %(data_source)s
    )
ON CONFLICT (uniprot_accession) DO UPDATE SET
    gene_name        = EXCLUDED.gene_name,
    protein_name     = EXCLUDED.protein_name,
    organism         = EXCLUDED.organism,
    sequence         = EXCLUDED.sequence,
    sequence_length  = EXCLUDED.sequence_length,
    molecular_weight = EXCLUDED.molecular_weight,
    annotation_score = EXCLUDED.annotation_score,
    data_source      = EXCLUDED.data_source,
    updated_at       = CURRENT_TIMESTAMP;
"""

_UPSERT_GENE = """
INSERT INTO silver.genes (uniprot_id, hgnc_symbol, gene_synonyms, data_source)
VALUES (%(uniprot_id)s, %(hgnc_symbol)s, %(gene_synonyms)s, %(data_source)s)
ON CONFLICT (uniprot_id) DO UPDATE SET
    hgnc_symbol   = EXCLUDED.hgnc_symbol,
    gene_synonyms = EXCLUDED.gene_synonyms,
    data_source   = EXCLUDED.data_source,
    updated_at    = CURRENT_TIMESTAMP;
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
    df = _with_protein_defaults(pl.read_csv(csv_path, null_values=[""]))
    _ensure_relational_schema(conn)
    rows = df.select(
        [
            "uniprot_id",
            "hgnc_symbol",
            "protein_name",
            "organism",
            "sequence",
            "sequence_length",
            "molecular_weight",
            "annotation_score",
            "data_source",
        ]
    ).to_dicts()
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_PROTEIN, rows)
    logger.info("Upserted %d protein rows", len(rows))
    return len(rows)


def load_genes(
    conn: psycopg.Connection,
    gene_map_csv_path: Path = SILVER_CSV_DIR / "silver_gene_symbol_map.csv",
    proteins_csv_path: Path = SILVER_CSV_DIR / "silver_proteins.csv",
) -> int:
    _ensure_relational_schema(conn)
    gene_map_df = pl.read_csv(gene_map_csv_path, null_values=[""])
    proteins_df = _with_protein_defaults(pl.read_csv(proteins_csv_path, null_values=[""]))
    rows = (
        gene_map_df.join(
            proteins_df.select(["uniprot_id", "gene_synonyms", "data_source"]),
            on="uniprot_id",
            how="left",
        )
        .with_columns(
            pl.coalesce([pl.col("gene_synonyms"), pl.lit("")]).alias("gene_synonyms"),
            pl.coalesce([pl.col("data_source"), pl.lit("UniProt")]).alias("data_source"),
        )
        .select(["uniprot_id", "hgnc_symbol", "gene_synonyms", "data_source"])
        .unique(subset=["uniprot_id"])
        .filter(pl.col("uniprot_id").str.strip_chars() != "")
        .sort("uniprot_id")
        .to_dicts()
    )
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

    _ensure_relational_schema(conn)
    pathway_rows = df.select(["reactome_id", "pathway_name"]).unique(
        subset=["reactome_id"]
    ).to_dicts()
    pp_rows = df.select(["uniprot_id", "reactome_id"]).unique().to_dicts()

    with conn.cursor() as cur:
        cur.executemany(_UPSERT_PATHWAY, pathway_rows)
        cur.executemany(_UPSERT_PROTEIN_PATHWAY, pp_rows)

    logger.info(
        "Upserted %d pathway rows and %d protein-pathway links",
        len(pathway_rows),
        len(pp_rows),
    )
    return len(pathway_rows) + len(pp_rows)


def _ensure_relational_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(_CREATE_SCHEMA)
        cur.execute(_CREATE_GENES)
        for statement in _ALTER_GENES:
            cur.execute(statement)
        for statement in _DROP_LEGACY_GENE_SYMBOL_UNIQUE:
            cur.execute(statement)
        cur.execute(_CREATE_GENES_UNIPROT_UNIQUE)
        cur.execute(_CREATE_PROTEINS)
        for statement in _ALTER_PROTEINS:
            cur.execute(statement)
        cur.execute(_CREATE_PATHWAYS)
        cur.execute(_CREATE_PROTEIN_PATHWAY)


def _with_protein_defaults(df: pl.DataFrame) -> pl.DataFrame:
    defaults: list[pl.Expr] = []
    if "sequence_length" not in df.columns:
        defaults.append(pl.lit(None, dtype=pl.Int64).alias("sequence_length"))
    if "annotation_score" not in df.columns:
        defaults.append(pl.lit(None, dtype=pl.Float64).alias("annotation_score"))
    if "gene_synonyms" not in df.columns:
        defaults.append(pl.lit("", dtype=pl.Utf8).alias("gene_synonyms"))
    if "data_source" not in df.columns:
        defaults.append(pl.lit("UniProt", dtype=pl.Utf8).alias("data_source"))
    if defaults:
        df = df.with_columns(defaults)
    return df


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run(dsn: str = PG_DSN) -> None:
    with psycopg.connect(dsn, autocommit=False) as conn:
        try:
            _ensure_relational_schema(conn)
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
