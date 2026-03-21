from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SEED_UNIPROT_ID = "P12345"
SEED_SYMBOL = "TEST_GENE"
SEED_MESH_ID = "M123"
SEED_DISEASE = "TEST_DISEASE"
SEED_CHEMBL_ID = "C123"
SEED_MEDICINE = "TEST_MED"


def seed() -> None:
    pg_db = os.getenv("POSTGRES_DB", "bionexus")
    pg_user = os.getenv("POSTGRES_USER", "bionexus_user")
    pg_pass = os.getenv("POSTGRES_PASSWORD", "bionexus_dev_password")
    pg_port = os.getenv("POSTGRES_PORT", "5433")

    conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host="localhost", port=pg_port)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO silver.genes (uniprot_id, hgnc_symbol, data_source)
            VALUES (%s, %s, 'Curated')
            ON CONFLICT (uniprot_id) DO NOTHING;
            """,
            (SEED_UNIPROT_ID, SEED_SYMBOL),
        )
    conn.commit()
    conn.close()

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_pass = os.getenv("NEO4J_PASSWORD", "bionexus_dev_password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_pass))
    with driver.session() as session:
        session.run(
            "MERGE (g:Gene {uniprot_id: $uniprot_id}) SET g.symbol = $symbol, g.name = $symbol, g.data_source = 'Curated'",
            uniprot_id=SEED_UNIPROT_ID,
            symbol=SEED_SYMBOL,
        )
        session.run(
            "MERGE (d:Disease {mesh_id: $mesh_id}) SET d.name = $name, d.organ = 'liver'",
            mesh_id=SEED_MESH_ID,
            name=SEED_DISEASE,
        )
        session.run(
            "MERGE (m:Medicine {chembl_id: $chembl_id}) SET m.name = $name, m.source = 'Curated'",
            chembl_id=SEED_CHEMBL_ID,
            name=SEED_MEDICINE,
        )
        session.run(
            """
            MATCH (g:Gene {uniprot_id: $uniprot_id}), (d:Disease {mesh_id: $mesh_id})
            MERGE (g)-[:ASSOCIATED_WITH {score: 0.9}]->(d)
            """,
            uniprot_id=SEED_UNIPROT_ID,
            mesh_id=SEED_MESH_ID,
        )
        session.run(
            """
            MATCH (m:Medicine {chembl_id: $chembl_id}), (d:Disease {mesh_id: $mesh_id})
            MERGE (m)-[:TREATS {phase: 3}]->(d)
            """,
            chembl_id=SEED_CHEMBL_ID,
            mesh_id=SEED_MESH_ID,
        )
        session.run(
            """
            MATCH (m:Medicine {chembl_id: $chembl_id}), (g:Gene {uniprot_id: $uniprot_id})
            MERGE (m)-[:BINDS_TO {affinity: 1.2}]->(g)
            """,
            chembl_id=SEED_CHEMBL_ID,
            uniprot_id=SEED_UNIPROT_ID,
        )
    driver.close()

if __name__ == '__main__':
    seed()
