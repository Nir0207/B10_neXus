-- BioNexus Postgres Initialization Script
-- Creates foundational schema for the Med-Data Lakehouse Silver layer

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS metadata;

-- Silver Layer: Refined Biological Entities
CREATE TABLE IF NOT EXISTS silver.proteins (
    protein_id SERIAL PRIMARY KEY,
    uniprot_accession VARCHAR(10) UNIQUE NOT NULL,
    gene_name VARCHAR(100),
    protein_name TEXT,
    organism VARCHAR(100) DEFAULT 'Homo sapiens',
    sequence TEXT,
    molecular_weight FLOAT,
    vector_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.genes (
    gene_id SERIAL PRIMARY KEY,
    hgnc_symbol VARCHAR(100) UNIQUE NOT NULL,
    ensembl_id VARCHAR(20),
    ncbi_gene_id INT,
    description TEXT,
    chromosome VARCHAR(5),
    start_position INT,
    end_position INT,
    strand CHAR(1),
    vector_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.diseases (
    disease_id SERIAL PRIMARY KEY,
    mondo_id VARCHAR(50) UNIQUE,
    disease_name VARCHAR(255) NOT NULL,
    description TEXT,
    icd10_code VARCHAR(10),
    phenotypes TEXT[],
    vector_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver.compounds (
    compound_id SERIAL PRIMARY KEY,
    chembl_id VARCHAR(20) UNIQUE,
    compound_name VARCHAR(255),
    smiles TEXT,
    molecular_weight FLOAT,
    logp FLOAT,
    vector_embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_uniprot_acc ON silver.proteins (uniprot_accession);
CREATE INDEX IF NOT EXISTS idx_gene_name ON silver.proteins (gene_name);
CREATE INDEX IF NOT EXISTS idx_hgnc ON silver.genes (hgnc_symbol);
CREATE INDEX IF NOT EXISTS idx_ensembl ON silver.genes (ensembl_id);
CREATE INDEX IF NOT EXISTS idx_mondo ON silver.diseases (mondo_id);
CREATE INDEX IF NOT EXISTS idx_disease_name ON silver.diseases (disease_name);
CREATE INDEX IF NOT EXISTS idx_chembl ON silver.compounds (chembl_id);

-- Metadata Layer: Data Lineage and Processing
CREATE TABLE IF NOT EXISTS metadata.data_source (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50),
    url VARCHAR(500),
    last_fetched TIMESTAMP,
    record_count INT DEFAULT 0,
    last_error TEXT,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS metadata.processing_log (
    log_id SERIAL PRIMARY KEY,
    source_id INT REFERENCES metadata.data_source(source_id),
    process_name VARCHAR(100),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    records_processed INT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize known data sources
INSERT INTO metadata.data_source (source_name, source_type, url, status) VALUES
    ('NCBI', 'API', 'https://www.ncbi.nlm.nih.gov/', 'active'),
    ('Open Targets', 'API', 'https://platform.opentargets.org/', 'active'),
    ('UniProt', 'API', 'https://www.uniprot.org/', 'active'),
    ('Reactome', 'API', 'https://reactome.org/', 'active'),
    ('BioGRID', 'API', 'https://thebiogrid.org/', 'active'),
    ('ChEMBL', 'API', 'https://www.ebi.ac.uk/chembl/', 'active')
ON CONFLICT DO NOTHING;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA silver TO bionexus_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA metadata TO bionexus_user;
