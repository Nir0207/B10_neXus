"""
Neo4j Silver-layer loader.

Merges nodes and relationships into the BioNexus knowledge graph:

    (:Gene {uniprot_id}) -[:INVOLVED_IN]-> (:Pathway {reactome_id})

All Cypher statements use MERGE for idempotency so re-running the loader
never creates duplicate nodes.
"""
from __future__ import annotations

import logging
from pathlib import Path

import polars as pl
from neo4j import Driver, GraphDatabase, ManagedTransaction

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, SILVER_CSV_DIR

logger = logging.getLogger(__name__)

# ── Cypher templates ─────────────────────────────────────────────────────────

_CREATE_CONSTRAINT_GENE = """
CREATE CONSTRAINT gene_uniprot_id_unique IF NOT EXISTS
FOR (g:Gene)
REQUIRE g.uniprot_id IS UNIQUE
"""

_CREATE_CONSTRAINT_PATHWAY = """
CREATE CONSTRAINT pathway_reactome_id_unique IF NOT EXISTS
FOR (pw:Pathway)
REQUIRE pw.reactome_id IS UNIQUE
"""

_MERGE_GENE_BATCH = """
UNWIND $rows AS row
MERGE (g:Gene {uniprot_id: row.uniprot_id})
ON CREATE SET
    g.symbol           = row.hgnc_symbol,
    g.name             = row.protein_name,
    g.uniprot_kb_id    = row.uniprot_kb_id,
    g.organism         = row.organism,
    g.sequence_length  = row.sequence_length,
    g.molecular_weight = row.molecular_weight,
    g.data_source      = row.data_source,
    g.created_at       = timestamp()
ON MATCH SET
    g.symbol           = row.hgnc_symbol,
    g.name             = row.protein_name,
    g.uniprot_kb_id    = row.uniprot_kb_id,
    g.organism         = row.organism,
    g.sequence_length  = row.sequence_length,
    g.molecular_weight = row.molecular_weight,
    g.data_source      = row.data_source,
    g.updated_at       = timestamp()
"""

_MERGE_PATHWAY_BATCH = """
UNWIND $rows AS row
MERGE (pw:Pathway {reactome_id: row.reactome_id})
ON CREATE SET pw.name = row.pathway_name, pw.created_at = timestamp()
ON MATCH SET  pw.name = row.pathway_name
"""

_MERGE_INVOLVED_IN_BATCH = """
UNWIND $rows AS row
MATCH (g:Gene {uniprot_id: row.uniprot_id})
MATCH (pw:Pathway {reactome_id:       row.reactome_id})
MERGE (g)-[:INVOLVED_IN]->(pw)
"""


# ── Loader helpers ────────────────────────────────────────────────────────────

def _ensure_constraints_tx(tx: ManagedTransaction) -> None:
    tx.run(_CREATE_CONSTRAINT_GENE)
    tx.run(_CREATE_CONSTRAINT_PATHWAY)


def _merge_genes_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, object]],
) -> None:
    tx.run(_MERGE_GENE_BATCH, rows=rows)


def _merge_pathways_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, str]],
) -> None:
    tx.run(_MERGE_PATHWAY_BATCH, rows=rows)


def _merge_involved_in_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, str]],
) -> None:
    tx.run(_MERGE_INVOLVED_IN_BATCH, rows=rows)


def _load_genes_and_proteins(
    driver: Driver,
    proteins_csv: Path,
    gene_map_csv: Path,
) -> None:
    proteins_df = _with_gene_defaults(pl.read_csv(proteins_csv, null_values=[""]))
    gene_map_df = pl.read_csv(gene_map_csv, null_values=[""]).select(["uniprot_id", "hgnc_symbol"])

    gene_rows: list[dict[str, object]] = (
        proteins_df.join(gene_map_df, on="uniprot_id", how="left", suffix="_map")
        .with_columns(
            pl.coalesce([pl.col("hgnc_symbol"), pl.col("hgnc_symbol_map")]).alias("hgnc_symbol")
        )
        .select(
            [
                "uniprot_id",
                "hgnc_symbol",
                "protein_name",
                "uniprot_kb_id",
                "organism",
                "sequence_length",
                "molecular_weight",
                "data_source",
            ]
        )
        .unique(subset=["uniprot_id"])
        .sort("uniprot_id")
        .to_dicts()
    )

    with driver.session() as session:
        session.execute_write(_ensure_constraints_tx)
        if gene_rows:
            session.execute_write(_merge_genes_tx, gene_rows)

    logger.info(
        "Loaded %d Gene nodes into Neo4j",
        len(gene_rows),
    )


def _load_pathways(driver: Driver, reactome_csv: Path) -> None:
    df = pl.read_csv(reactome_csv, null_values=[""])
    if df.is_empty():
        return

    pathway_rows: list[dict[str, str]] = df.select(
        ["reactome_id", "pathway_name"]
    ).unique(subset=["reactome_id"]).to_dicts()
    involved_rows: list[dict[str, str]] = df.select(
        ["uniprot_id", "reactome_id"]
    ).unique().to_dicts()

    with driver.session() as session:
        session.execute_write(_ensure_constraints_tx)
        session.execute_write(_merge_pathways_tx, pathway_rows)
        session.execute_write(_merge_involved_in_tx, involved_rows)

    logger.info(
        "Loaded %d Pathway nodes and %d INVOLVED_IN edges",
        len(pathway_rows),
        len(involved_rows),
    )


def _with_gene_defaults(df: pl.DataFrame) -> pl.DataFrame:
    defaults: list[pl.Expr] = []
    if "data_source" not in df.columns:
        defaults.append(pl.lit("UniProt", dtype=pl.Utf8).alias("data_source"))
    if "sequence_length" not in df.columns:
        defaults.append(pl.lit(None, dtype=pl.Int64).alias("sequence_length"))
    if "molecular_weight" not in df.columns:
        defaults.append(pl.lit(None, dtype=pl.Int64).alias("molecular_weight"))
    if defaults:
        df = df.with_columns(defaults)
    return df


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run(
    uri: str = NEO4J_URI,
    user: str = NEO4J_USER,
    password: str = NEO4J_PASSWORD,
) -> None:
    driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        _load_genes_and_proteins(
            driver,
            SILVER_CSV_DIR / "silver_proteins.csv",
            SILVER_CSV_DIR / "silver_gene_symbol_map.csv",
        )
        _load_pathways(driver, SILVER_CSV_DIR / "silver_reactome_map.csv")
        logger.info("Neo4j Silver load complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
