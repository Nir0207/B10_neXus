import os
import psycopg2
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def seed():
    PG_DB = os.getenv("POSTGRES_DB", "bionexus")
    PG_USER = os.getenv("POSTGRES_USER", "bionexus_user")
    PG_PASS = os.getenv("POSTGRES_PASSWORD", "bionexus_dev_password")
    PG_PORT = os.getenv("POSTGRES_PORT", "5433")
    
    conn = psycopg2.connect(dbname=PG_DB, user=PG_USER, password=PG_PASS, host="localhost", port=PG_PORT)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO genes (uniprot_id, hgnc_symbol) VALUES ('P12345', 'TEST_GENE') ON CONFLICT DO NOTHING;")
    conn.commit()
    conn.close()

    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "bionexus_dev_password")
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        session.run("MERGE (g:Gene {uniprot_id: 'P12345', symbol: 'TEST_GENE'})")
        session.run("MERGE (d:Disease {mesh_id: 'M123', name: 'TEST_DISEASE'})")
        session.run("MERGE (m:Medicine {chembl_id: 'C123', name: 'TEST_MED'})")
        session.run("MATCH (g:Gene {uniprot_id: 'P12345'}), (d:Disease {mesh_id: 'M123'}) MERGE (g)-[:ASSOCIATED_WITH {score: 0.9}]->(d)")
        session.run("MATCH (m:Medicine {chembl_id: 'C123'}), (d:Disease {mesh_id: 'M123'}) MERGE (m)-[:TREATS {phase: 3}]->(d)")
        session.run("MATCH (m:Medicine {chembl_id: 'C123'}), (g:Gene {uniprot_id: 'P12345'}) MERGE (m)-[:BINDS_TO {affinity: 1.2}]->(g)")
    driver.close()

if __name__ == '__main__':
    seed()
