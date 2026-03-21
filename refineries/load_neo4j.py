"""
Neo4j Silver-layer loader.

Merges nodes and relationships into the BioNexus knowledge graph:

    (:Gene {hgnc_symbol})  -[:ENCODES]->    (:Protein {uniprot_accession})
    (:Protein)             -[:INVOLVED_IN]-> (:Pathway  {reactome_id})

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
CREATE CONSTRAINT gene_hgnc_symbol_unique IF NOT EXISTS
FOR (g:Gene)
REQUIRE g.hgnc_symbol IS UNIQUE
"""

_CREATE_CONSTRAINT_PROTEIN = """
CREATE CONSTRAINT protein_uniprot_accession_unique IF NOT EXISTS
FOR (p:Protein)
REQUIRE p.uniprot_accession IS UNIQUE
"""

_CREATE_CONSTRAINT_PATHWAY = """
CREATE CONSTRAINT pathway_reactome_id_unique IF NOT EXISTS
FOR (pw:Pathway)
REQUIRE pw.reactome_id IS UNIQUE
"""

_MERGE_PROTEIN_BATCH = """
UNWIND $rows AS row
MERGE (p:Protein {uniprot_accession: row.uniprot_id})
ON CREATE SET
    p.name             = row.protein_name,
    p.uniprot_kb_id    = row.uniprot_kb_id,
    p.organism         = row.organism,
    p.sequence_length  = row.sequence_length,
    p.molecular_weight = row.molecular_weight,
    p.created_at       = timestamp()
ON MATCH SET
    p.name             = row.protein_name,
    p.sequence_length  = row.sequence_length,
    p.molecular_weight = row.molecular_weight,
    p.updated_at       = timestamp()
"""

_MERGE_GENE_BATCH = """
UNWIND $rows AS row
MERGE (g:Gene {hgnc_symbol: row.hgnc_symbol})
ON CREATE SET g.created_at = timestamp()
"""

_MERGE_ENCODES_BATCH = """
UNWIND $rows AS row
MATCH (g:Gene    {hgnc_symbol: row.hgnc_symbol})
MATCH (p:Protein {uniprot_accession: row.uniprot_id})
MERGE (g)-[:ENCODES]->(p)
"""

_MERGE_PATHWAY_BATCH = """
UNWIND $rows AS row
MERGE (pw:Pathway {reactome_id: row.reactome_id})
ON CREATE SET pw.name = row.pathway_name, pw.created_at = timestamp()
ON MATCH SET  pw.name = row.pathway_name
"""

_MERGE_INVOLVED_IN_BATCH = """
UNWIND $rows AS row
MATCH (p:Protein {uniprot_accession: row.uniprot_id})
MATCH (pw:Pathway {reactome_id:       row.reactome_id})
MERGE (p)-[:INVOLVED_IN]->(pw)
"""


# ── Loader helpers ────────────────────────────────────────────────────────────

def _ensure_constraints_tx(tx: ManagedTransaction) -> None:
    tx.run(_CREATE_CONSTRAINT_GENE)
    tx.run(_CREATE_CONSTRAINT_PROTEIN)
    tx.run(_CREATE_CONSTRAINT_PATHWAY)


def _merge_proteins_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, object]],
) -> None:
    tx.run(_MERGE_PROTEIN_BATCH, rows=rows)


def _merge_genes_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, str]],
) -> None:
    tx.run(_MERGE_GENE_BATCH, rows=rows)


def _merge_encodes_tx(
    tx: ManagedTransaction,
    rows: list[dict[str, str]],
) -> None:
    tx.run(_MERGE_ENCODES_BATCH, rows=rows)


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
    proteins_df = pl.read_csv(proteins_csv, null_values=[""])
    gene_map_df = pl.read_csv(gene_map_csv, null_values=[""])

    proteins_rows: list[dict[str, object]] = [
        {
            "uniprot_id": row["uniprot_id"],
            "protein_name": row.get("protein_name") or "",
            "uniprot_kb_id": row.get("uniprot_kb_id") or "",
            "organism": row.get("organism") or "Homo sapiens",
            "sequence_length": row.get("sequence_length"),
            "molecular_weight": row.get("molecular_weight"),
        }
        for row in proteins_df.to_dicts()
    ]
    gene_rows: list[dict[str, str]] = [
        {"hgnc_symbol": symbol}
        for symbol in gene_map_df["gene_symbol"].unique().to_list()
        if symbol
    ]
    encodes_rows: list[dict[str, str]] = proteins_df.filter(
        pl.col("hgnc_symbol") != ""
    ).select(["hgnc_symbol", "uniprot_id"]).unique().to_dicts()

    with driver.session() as session:
        session.execute_write(_ensure_constraints_tx)
        if proteins_rows:
            session.execute_write(_merge_proteins_tx, proteins_rows)
        if gene_rows:
            session.execute_write(_merge_genes_tx, gene_rows)
        if encodes_rows:
            session.execute_write(_merge_encodes_tx, encodes_rows)

    logger.info(
        "Loaded %d Protein nodes and %d Gene nodes into Neo4j",
        len(proteins_rows),
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
