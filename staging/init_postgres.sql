CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.genes (
    uniprot_id VARCHAR(15) PRIMARY KEY,
    hgnc_symbol VARCHAR(64) NOT NULL,
    gene_synonyms TEXT NOT NULL DEFAULT '',
    data_source TEXT NOT NULL DEFAULT 'UniProt',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.proteins (
    uniprot_accession VARCHAR(15) PRIMARY KEY,
    gene_name VARCHAR(64) NOT NULL,
    protein_name TEXT NOT NULL,
    organism TEXT NOT NULL,
    sequence TEXT NOT NULL,
    sequence_length INTEGER,
    molecular_weight BIGINT,
    annotation_score DOUBLE PRECISION,
    data_source TEXT NOT NULL DEFAULT 'UniProt',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.pathways (
    reactome_id VARCHAR(20) PRIMARY KEY,
    pathway_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.protein_pathway (
    uniprot_id VARCHAR(15) NOT NULL REFERENCES silver.genes (uniprot_id),
    reactome_id VARCHAR(20) NOT NULL REFERENCES silver.pathways (reactome_id),
    PRIMARY KEY (uniprot_id, reactome_id)
);

CREATE TABLE IF NOT EXISTS disease_catalog (
    mesh_id VARCHAR(32) PRIMARY KEY,
    name TEXT NOT NULL,
    organ VARCHAR(64),
    source TEXT NOT NULL DEFAULT 'Curated'
);

CREATE TABLE IF NOT EXISTS medicine_catalog (
    chembl_id VARCHAR(32) PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'Curated'
);

CREATE TABLE IF NOT EXISTS gene_disease_associations (
    uniprot_id VARCHAR(15) NOT NULL REFERENCES silver.genes (uniprot_id),
    mesh_id VARCHAR(32) NOT NULL REFERENCES disease_catalog (mesh_id),
    score DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (uniprot_id, mesh_id)
);

CREATE TABLE IF NOT EXISTS medicine_disease_treatments (
    chembl_id VARCHAR(32) NOT NULL REFERENCES medicine_catalog (chembl_id),
    mesh_id VARCHAR(32) NOT NULL REFERENCES disease_catalog (mesh_id),
    phase INTEGER,
    PRIMARY KEY (chembl_id, mesh_id)
);

CREATE TABLE IF NOT EXISTS medicine_gene_bindings (
    chembl_id VARCHAR(32) NOT NULL REFERENCES medicine_catalog (chembl_id),
    uniprot_id VARCHAR(15) NOT NULL REFERENCES silver.genes (uniprot_id),
    affinity DOUBLE PRECISION,
    PRIMARY KEY (chembl_id, uniprot_id)
);

CREATE TABLE IF NOT EXISTS ncbi_studies (
    uid VARCHAR(32) PRIMARY KEY,
    accession VARCHAR(32) NOT NULL,
    gene_symbol VARCHAR(64),
    title TEXT NOT NULL,
    summary TEXT,
    taxon TEXT,
    gds_type TEXT,
    entry_type TEXT,
    publication_date TEXT,
    sample_count INTEGER NOT NULL DEFAULT 0,
    platform TEXT,
    source_file TEXT
);

-- B-Tree index for case-insensitive UniProt lookups during staging merges.
-- Exact lookups are already indexed by the PRIMARY KEY.
CREATE INDEX IF NOT EXISTS idx_silver_genes_uniprot_id_lower
    ON silver.genes USING BTREE (LOWER(uniprot_id));

CREATE OR REPLACE VIEW genes AS
SELECT
    g.uniprot_id,
    g.hgnc_symbol AS gene_symbol,
    p.protein_name AS name,
    NULL::TEXT AS description,
    g.data_source
FROM silver.genes AS g
LEFT JOIN silver.proteins AS p
    ON p.uniprot_accession = g.uniprot_id;

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    record_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS app_users (
    username VARCHAR(32) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(120),
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_email_lower
    ON app_users (LOWER(email));
