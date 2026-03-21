#!/usr/bin/env python3
"""
BioNexus DuckDB Lake Initializer

Initializes the local Med-Data Lakehouse Bronze layer:
- Creates DuckDB database and schema
- Establishes Parquet partitioning structure
- Registers external biological data sources
- Creates views for data quality checks
- Enables incremental loading capabilities
"""

import os
import sys
from pathlib import Path
import duckdb
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DuckDBLakeInitializer:
    """Initializes and manages the DuckDB-based Med-Data Lakehouse."""
    
    def __init__(self, db_path: str = "data_lake/bionexus.duckdb"):
        """
        Initialize the DuckDB lake initializer.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.db_dir = Path(db_path).parent
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Data lake structure
        self.lake_dir = self.db_dir / "bronze"
        self.lake_dir.mkdir(exist_ok=True)
        
        # Initialize connection
        self.conn = duckdb.connect(db_path)
        self.conn.execute("INSTALL parquet;")
        self.conn.execute("LOAD parquet;")
        
        logger.info(f"Initialized DuckDB connection: {db_path}")
    
    def create_bronze_schema(self) -> None:
        """Create the Bronze layer schema for raw ingestion."""
        logger.info("Creating Bronze layer schema...")
        
        self.conn.execute("""
            CREATE SCHEMA IF NOT EXISTS bronze;
        """)
        
        # Create ingestion tables for each major data source
        self._create_ingestion_tables()
        
        logger.info("✓ Bronze schema created successfully")
    
    def _create_ingestion_tables(self) -> None:
        """Create tables for different biological data sources."""
        
        # NCBI Gene Expression table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.ncbi_geo_raw (
                accession_id VARCHAR,
                title VARCHAR,
                summary VARCHAR,
                platform VARCHAR,
                sample_count INTEGER,
                status VARCHAR,
                submission_date DATE,
                raw_json JSON,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created ncbi_geo_raw table")
        
        # UniProt Proteins table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.uniprot_proteins_raw (
                uniprot_id VARCHAR,
                entry_name VARCHAR,
                protein_name VARCHAR,
                organism VARCHAR,
                sequence VARCHAR,
                gene_names VARCHAR,
                keywords VARCHAR[],
                comments VARCHAR,
                raw_xml VARCHAR,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created uniprot_proteins_raw table")
        
        # Open Targets Drug-Target table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.open_targets_raw (
                target_id VARCHAR,
                drug_id VARCHAR,
                target_name VARCHAR,
                drug_name VARCHAR,
                disease_id VARCHAR,
                disease_name VARCHAR,
                clinical_phase VARCHAR,
                evidence_score FLOAT,
                raw_json JSON,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created open_targets_raw table")
        
        # Reactome Pathways table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.reactome_pathways_raw (
                pathway_id VARCHAR,
                pathway_name VARCHAR,
                description VARCHAR,
                species VARCHAR,
                reaction_ids VARCHAR[],
                protein_ids VARCHAR[],
                raw_json JSON,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created reactome_pathways_raw table")
        
        # BioGRID Interactions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.biogrid_interactions_raw (
                interaction_id INTEGER,
                genea_offical_id VARCHAR,
                geneb_offical_id VARCHAR,
                genea_name VARCHAR,
                geneb_name VARCHAR,
                interaction_type VARCHAR[],
                organism_id INTEGER,
                throughput VARCHAR,
                score FLOAT,
                pubmed_id VARCHAR[],
                raw_tsv VARCHAR,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created biogrid_interactions_raw table")
        
        # ChEMBL Compounds table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.chembl_compounds_raw (
                chembl_id VARCHAR,
                molecule_name VARCHAR,
                smiles VARCHAR,
                inchi VARCHAR,
                molecular_weight FLOAT,
                logp FLOAT,
                hba INTEGER,
                hbd INTEGER,
                rotatable_bonds INTEGER,
                targets VARCHAR[],
                raw_json JSON,
                ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_id VARCHAR
            );
        """)
        logger.info("  ✓ Created chembl_compounds_raw table")
        
        # Create sequence for audit IDs before using nextval
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS audit_seq START WITH 1;
        """)
        
        # Create ingestion audit table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.ingestion_audit (
                audit_id INTEGER PRIMARY KEY DEFAULT nextval('audit_seq'),
                source_name VARCHAR,
                table_name VARCHAR,
                batch_id VARCHAR UNIQUE,
                record_count INTEGER,
                ingestion_start TIMESTAMP,
                ingestion_end TIMESTAMP,
                status VARCHAR,
                error_message VARCHAR
            );
        """)
        logger.info("  ✓ Created ingestion_audit table")
    
    def create_bronze_views(self) -> None:
        """Create views for data discovery and validation."""
        logger.info("Creating Bronze layer views...")
        
        # View: Latest ingestions per source
        self.conn.execute("""
            CREATE VIEW IF NOT EXISTS bronze.v_latest_ingestions AS
            SELECT 
                source_name,
                table_name,
                batch_id,
                record_count,
                ingestion_end,
                status,
                ROW_NUMBER() OVER (PARTITION BY source_name ORDER BY ingestion_end DESC) as rn
            FROM bronze.ingestion_audit
            WHERE status = 'success'
            QUALIFY rn = 1;
        """)
        logger.info("  ✓ Created v_latest_ingestions view")
        
        # View: Ingestion summary by source
        self.conn.execute("""
            CREATE VIEW IF NOT EXISTS bronze.v_ingestion_summary AS
            SELECT 
                source_name,
                COUNT(*) as total_batches,
                SUM(record_count) as total_records,
                MAX(ingestion_end) as last_ingestion,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_batches,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_batches
            FROM bronze.ingestion_audit
            GROUP BY source_name;
        """)
        logger.info("  ✓ Created v_ingestion_summary view")
        
        # View: Data quality checks
        self.conn.execute("""
            CREATE VIEW IF NOT EXISTS bronze.v_data_quality_checks AS
            SELECT 
                'ncbi_geo_raw' as table_name,
                COUNT(*) as row_count,
                COUNT(DISTINCT batch_id) as batch_count,
                MAX(ingestion_timestamp) as latest_ingestion,
                COUNT(CASE WHEN accession_id IS NULL THEN 1 END) as null_accessions
            FROM bronze.ncbi_geo_raw
            UNION ALL
            SELECT 
                'uniprot_proteins_raw' as table_name,
                COUNT(*),
                COUNT(DISTINCT batch_id),
                MAX(ingestion_timestamp),
                COUNT(CASE WHEN uniprot_id IS NULL THEN 1 END)
            FROM bronze.uniprot_proteins_raw
            UNION ALL
            SELECT 
                'open_targets_raw' as table_name,
                COUNT(*),
                COUNT(DISTINCT batch_id),
                MAX(ingestion_timestamp),
                COUNT(CASE WHEN target_id IS NULL OR drug_id IS NULL THEN 1 END)
            FROM bronze.open_targets_raw
            UNION ALL
            SELECT 
                'reactome_pathways_raw' as table_name,
                COUNT(*),
                COUNT(DISTINCT batch_id),
                MAX(ingestion_timestamp),
                COUNT(CASE WHEN pathway_id IS NULL THEN 1 END)
            FROM bronze.reactome_pathways_raw
            UNION ALL
            SELECT 
                'biogrid_interactions_raw' as table_name,
                COUNT(*),
                COUNT(DISTINCT batch_id),
                MAX(ingestion_timestamp),
                COUNT(CASE WHEN genea_offical_id IS NULL OR geneb_offical_id IS NULL THEN 1 END)
            FROM bronze.biogrid_interactions_raw
            UNION ALL
            SELECT 
                'chembl_compounds_raw' as table_name,
                COUNT(*),
                COUNT(DISTINCT batch_id),
                MAX(ingestion_timestamp),
                COUNT(CASE WHEN chembl_id IS NULL THEN 1 END)
            FROM bronze.chembl_compounds_raw;
        """)
        logger.info("  ✓ Created v_data_quality_checks view")
        
        logger.info("✓ Bronze views created successfully")
    
    def create_silver_schema(self) -> None:
        """Create the Silver layer schema for refined data."""
        logger.info("Creating Silver layer schema...")
        
        self.conn.execute("""
            CREATE SCHEMA IF NOT EXISTS silver;
        """)
        
        # Silver layer refined tables (partitioned by ingestion date)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.proteins_refined (
                protein_id INTEGER PRIMARY KEY,
                uniprot_accession VARCHAR UNIQUE,
                gene_name VARCHAR,
                protein_name VARCHAR,
                organism VARCHAR,
                sequence VARCHAR,
                molecular_weight FLOAT,
                ncbi_gene_id INTEGER,
                data_quality_score FLOAT,
                last_updated TIMESTAMP,
                data_source VARCHAR,
                ingestion_date DATE
            );
        """)
        logger.info("  ✓ Created proteins_refined table")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.genes_refined (
                gene_id INTEGER PRIMARY KEY,
                hgnc_symbol VARCHAR UNIQUE,
                ensembl_id VARCHAR,
                ncbi_gene_id INTEGER UNIQUE,
                description VARCHAR,
                chromosome VARCHAR,
                start_position INTEGER,
                end_position INTEGER,
                strand CHAR(1),
                data_quality_score FLOAT,
                last_updated TIMESTAMP,
                data_source VARCHAR,
                ingestion_date DATE
            );
        """)
        logger.info("  ✓ Created genes_refined table")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.diseases_refined (
                disease_id INTEGER PRIMARY KEY,
                mondo_id VARCHAR UNIQUE,
                disease_name VARCHAR,
                icd10_code VARCHAR,
                description VARCHAR,
                phenotypes VARCHAR[],
                associated_genes VARCHAR[],
                data_quality_score FLOAT,
                last_updated TIMESTAMP,
                data_source VARCHAR,
                ingestion_date DATE
            );
        """)
        logger.info("  ✓ Created diseases_refined table")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.compounds_refined (
                compound_id INTEGER PRIMARY KEY,
                chembl_id VARCHAR UNIQUE,
                compound_name VARCHAR,
                smiles VARCHAR,
                inchi VARCHAR,
                molecular_weight FLOAT,
                logp FLOAT,
                target_proteins VARCHAR[],
                therapeutic_areas VARCHAR[],
                data_quality_score FLOAT,
                last_updated TIMESTAMP,
                data_source VARCHAR,
                ingestion_date DATE
            );
        """)
        logger.info("  ✓ Created compounds_refined table")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS silver.protein_interactions (
                interaction_id INTEGER PRIMARY KEY,
                protein_a_id INTEGER,
                protein_b_id INTEGER,
                interaction_type VARCHAR,
                evidence_score FLOAT,
                pubmed_ids VARCHAR[],
                data_quality_score FLOAT,
                last_updated TIMESTAMP,
                data_source VARCHAR,
                ingestion_date DATE
            );
        """)
        logger.info("  ✓ Created protein_interactions table")
        
        logger.info("✓ Silver schema created successfully")
    
    def create_parquet_registry(self) -> None:
        """Create registry for Parquet files in the lake."""
        logger.info("Creating Parquet registry...")
        
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS parquet_seq START WITH 1;
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bronze.parquet_registry (
                registry_id INTEGER PRIMARY KEY DEFAULT nextval('parquet_seq'),
                file_path VARCHAR,
                table_name VARCHAR,
                data_source VARCHAR,
                record_count INTEGER,
                file_size_bytes INTEGER,
                created_date DATE,
                partitions VARCHAR[],
                compression VARCHAR DEFAULT 'snappy'
            );
        """)
        
        logger.info("✓ Parquet registry created successfully")
    
    def initialize_all(self) -> None:
        """Run all initialization steps."""
        logger.info("=" * 60)
        logger.info("🧬 BioNexus DuckDB Lake Initialization")
        logger.info("=" * 60)
        
        try:
            self.create_bronze_schema()
            self.create_bronze_views()
            self.create_silver_schema()
            self.create_parquet_registry()
            
            # Display summary
            logger.info("=" * 60)
            logger.info("✅ INITIALIZATION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Database: {self.db_path}")
            logger.info(f"Lake Directory: {self.lake_dir}")
            logger.info("")
            logger.info("Schema Summary:")
            schemas = self.conn.execute("""
                SELECT table_schema AS schema_name, COUNT(*) as object_count
                FROM information_schema.tables
                WHERE table_schema NOT IN ('memory', 'temp', 'system')
                GROUP BY table_schema;
            """).fetchall()
            
            for schema, count in schemas:
                logger.info(f"  • {schema}: {count} objects")
            
            logger.info("")
            logger.info("Data Quality Views Available:")
            logger.info("  • v_latest_ingestions")
            logger.info("  • v_ingestion_summary")
            logger.info("  • v_data_quality_checks")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            sys.exit(1)
    
    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    db_path = os.getenv("DUCKDB_PATH", "data_lake/bionexus.duckdb")
    
    initializer = DuckDBLakeInitializer(db_path)
    try:
        initializer.initialize_all()
    finally:
        initializer.close()


if __name__ == "__main__":
    main()
