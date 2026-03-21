CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS studies (
    NCT_ID VARCHAR(50) PRIMARY KEY,
    Title TEXT NOT NULL,
    Organ VARCHAR(100),
    Source VARCHAR(50),
    Abstract_Vector VECTOR(768)
);

CREATE TABLE IF NOT EXISTS genes (
    UniProt_ID VARCHAR(50) PRIMARY KEY,
    HGNC_Symbol VARCHAR(50) NOT NULL,
    Protein_Name TEXT,
    Function TEXT
);

-- B-Tree index for case-insensitive UniProt lookups during staging merges.
-- Exact lookups are already indexed by the PRIMARY KEY.
CREATE INDEX IF NOT EXISTS idx_genes_uniprot_id_lower
    ON genes USING BTREE (LOWER(UniProt_ID));

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    record_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50)
);
