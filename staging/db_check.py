from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

if TYPE_CHECKING:
    from neo4j import Driver
    from psycopg2.extensions import connection as PGConnection
else:
    Driver = Any
    PGConnection = Any

load_dotenv()

# Postgres connection
PG_USER = os.getenv("POSTGRES_USER", "bionexus")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "bionexus_pass")
PG_DB = os.getenv("POSTGRES_DB", "bionexus_db")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "bionexus_pass")

REQUIRED_NEO4J_CONSTRAINT_DDL: dict[str, str] = {
    "gene_uniprot_id": "CREATE CONSTRAINT gene_uniprot_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.uniprot_id IS UNIQUE",
    "disease_mesh_id": "CREATE CONSTRAINT disease_mesh_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.mesh_id IS UNIQUE",
    "medicine_chembl_id": "CREATE CONSTRAINT medicine_chembl_id IF NOT EXISTS FOR (m:Medicine) REQUIRE m.chembl_id IS UNIQUE",
    "pathway_reactome_id": "CREATE CONSTRAINT pathway_reactome_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.reactome_id IS UNIQUE",
}

REQUIRED_NEO4J_INDEX_DDL: dict[str, str] = {
    "disease_name_fulltext": "CREATE FULLTEXT INDEX disease_name_fulltext IF NOT EXISTS FOR (d:Disease) ON EACH [d.name]",
}


def get_postgres_connection() -> PGConnection:
    import psycopg2

    return psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        host=PG_HOST,
        port=PG_PORT,
    )


def get_neo4j_driver() -> Driver:
    from neo4j import GraphDatabase

    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def audit_and_fix_neo4j_schema(auto_fix: bool = True) -> tuple[bool, list[str], list[str]]:
    """
    Audit required Neo4j constraints/indexes and optionally create missing ones.

    Returns
    -------
    (is_valid, issues, applied_fixes)
    """
    neo4j_driver: Driver | None = None
    issues: list[str] = []
    applied_fixes: list[str] = []

    try:
        neo4j_driver = get_neo4j_driver()
        with neo4j_driver.session() as session:
            constraint_rows = session.run("SHOW CONSTRAINTS YIELD name RETURN name")
            index_rows = session.run("SHOW INDEXES YIELD name RETURN name")

            existing_constraints = {
                str(row.get("name", "")).strip()
                for row in constraint_rows
                if str(row.get("name", "")).strip()
            }
            existing_indexes = {
                str(row.get("name", "")).strip()
                for row in index_rows
                if str(row.get("name", "")).strip()
            }

            missing_constraints = [
                name for name in REQUIRED_NEO4J_CONSTRAINT_DDL if name not in existing_constraints
            ]
            missing_indexes = [
                name for name in REQUIRED_NEO4J_INDEX_DDL if name not in existing_indexes
            ]

            if not auto_fix:
                for name in missing_constraints:
                    issues.append(f"Missing required Neo4j constraint: {name}")
                for name in missing_indexes:
                    issues.append(f"Missing required Neo4j index: {name}")
            else:
                for name in missing_constraints:
                    session.run(REQUIRED_NEO4J_CONSTRAINT_DDL[name])
                    applied_fixes.append(name)
                for name in missing_indexes:
                    session.run(REQUIRED_NEO4J_INDEX_DDL[name])
                    applied_fixes.append(name)

    except Exception as exc:
        issues.append(f"Exception during Neo4j schema audit: {exc}")
    finally:
        if neo4j_driver:
            neo4j_driver.close()

    return len(issues) == 0, issues, applied_fixes


def check_uniprot_consistency() -> tuple[bool, set[str]]:
    """
    Verify that all UniProt IDs in Postgres `genes` are present as Neo4j `:Gene` IDs.

    Returns
    -------
    (consistent, missing_in_neo4j)
    """
    pg_conn: PGConnection | None = None
    neo4j_driver: Driver | None = None

    try:
        pg_conn = get_postgres_connection()
        neo4j_driver = get_neo4j_driver()

        with pg_conn.cursor() as cur:
            pg_genes = _fetch_postgres_uniprot_ids(cur)

        with neo4j_driver.session() as session:
            result = session.run("MATCH (g:Gene) RETURN g.uniprot_id AS uniprot_id")
            neo4j_genes = {
                _normalize_uniprot_id(record.get("uniprot_id"))
                for record in result
                if _normalize_uniprot_id(record.get("uniprot_id"))
            }

        missing_in_neo4j = pg_genes - neo4j_genes
        return len(missing_in_neo4j) == 0, missing_in_neo4j

    except Exception:
        return False, set()
    finally:
        if pg_conn:
            pg_conn.close()
        if neo4j_driver:
            neo4j_driver.close()


def check_gene_disease_medicine_integrity(limit: int = 500) -> tuple[bool, list[str]]:
    """
    Verify that Gene -> Disease <- Medicine triads are traversable and complete.
    """
    neo4j_driver: Driver | None = None
    issues: list[str] = []
    seen_paths: set[tuple[str, str, str]] = set()

    triad_query = """
    MATCH (g:Gene)-[:ASSOCIATED_WITH]->(d:Disease)<-[:TREATS]-(m:Medicine)
    RETURN
        g.uniprot_id AS gene_uniprot_id,
        d.mesh_id AS disease_mesh_id,
        d.name AS disease_name,
        m.chembl_id AS medicine_chembl_id
    LIMIT $limit
    """

    try:
        neo4j_driver = get_neo4j_driver()
        with neo4j_driver.session() as session:
            result = session.run(triad_query, limit=limit)
            records = [dict(record) for record in result]

        if not records:
            issues.append("No Gene -> Disease -> Medicine triads were returned.")

        for row_number, row in enumerate(records, start=1):
            gene_uniprot_id = _normalize_uniprot_id(row.get("gene_uniprot_id"))
            disease_mesh_id = str(row.get("disease_mesh_id", "")).strip()
            disease_name = str(row.get("disease_name", "")).strip()
            medicine_chembl_id = str(row.get("medicine_chembl_id", "")).strip()

            if not gene_uniprot_id:
                issues.append(f"Row {row_number}: missing gene_uniprot_id.")
            if not disease_mesh_id:
                issues.append(f"Row {row_number}: missing disease_mesh_id.")
            if not disease_name:
                issues.append(f"Row {row_number}: missing disease_name.")
            if not medicine_chembl_id:
                issues.append(f"Row {row_number}: missing medicine_chembl_id.")

            triad_key = (gene_uniprot_id, disease_mesh_id, medicine_chembl_id)
            if triad_key in seen_paths:
                issues.append(f"Row {row_number}: duplicate triad path detected ({triad_key}).")
            else:
                seen_paths.add(triad_key)

    except Exception as exc:
        issues.append(f"Exception during triad integrity check: {exc}")
    finally:
        if neo4j_driver:
            neo4j_driver.close()

    return len(issues) == 0, issues


def _normalize_uniprot_id(value: Any) -> str:
    text = str(value or "").strip().upper()
    return text


def _fetch_postgres_uniprot_ids(cursor: Any) -> set[str]:
    # Support either legacy "UniProt_ID" or normalized lowercase "uniprot_id".
    for query in (
        "SELECT uniprot_id FROM silver.genes;",
        "SELECT uniprot_id FROM genes;",
        'SELECT "UniProt_ID" FROM genes;',
    ):
        try:
            cursor.execute(query)
            return {
                _normalize_uniprot_id(row[0])
                for row in cursor.fetchall()
                if _normalize_uniprot_id(row[0])
            }
        except Exception:
            continue

    raise RuntimeError("Could not query UniProt IDs from Postgres genes table.")


if __name__ == "__main__":
    schema_ok, schema_issues, schema_fixes = audit_and_fix_neo4j_schema(auto_fix=True)
    if schema_fixes:
        print(f"Applied Neo4j schema fixes: {schema_fixes}")
    if not schema_ok:
        print(f"Neo4j schema audit failed: {schema_issues}")
        sys.exit(1)

    uniprot_ok, missing_ids = check_uniprot_consistency()
    if not uniprot_ok:
        print(f"UniProt consistency check failed. Missing in Neo4j: {sorted(missing_ids)}")
        sys.exit(1)

    triad_ok, triad_issues = check_gene_disease_medicine_integrity()
    if not triad_ok:
        print(f"Triad integrity check failed: {triad_issues}")
        sys.exit(1)

    print("Staging integrity checks passed.")
    sys.exit(0)
