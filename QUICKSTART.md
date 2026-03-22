# 🚀 Quick Start Guide

## First Time Setup

Before starting containers, create your local env files:

- See [env/SETUP.md](/BioNexus/env/SETUP.md) for the full key checklist
- See [README.md](/BioNexus/README.md#L230) for the current first-time container startup order

### 1. Start Services (2 minutes)
```bash
make init
```

This will:
- Install Python dependencies
- Start Docker services (Postgres, Neo4j, MongoDB)
- Initialize the DuckDB lake
- Run health checks

### 2. Verify Everything Works
```bash
make health
```

---

## Common Tasks

### 📊 Access Databases

**Postgres (Relational)**
```bash
make postgres-shell
```
Then in psql:
```sql
-- View available tables
\dt silver.*

-- Query proteins
SELECT uniprot_accession, gene_name FROM silver.proteins LIMIT 10;

-- Check ingestion status
SELECT * FROM metadata.data_source;
```

**Neo4j (Knowledge Graph)**
```bash
make neo4j-shell
```
Then in Cypher:
```cypher
-- View knowledge graph
MATCH (n) RETURN count(n) as total_nodes;

-- Create test gene node
CREATE (g:Gene {name: "TP53", hgnc_symbol: "TP53"});

-- Find relationships
MATCH (p:Protein)-[:TARGETS]-(c:Compound) RETURN p, c LIMIT 5;
```

Browser: http://localhost:7474

**MongoDB (Document Store)**
```bash
make mongo-shell
```
Then:
```javascript
// View collections
show collections;

// Check ingestion status
db.ingestion_audit.find().pretty();

// View raw data
db.raw_ingestions.findOne();
```

### 🦆 Query DuckDB Lake

```bash
python3 << 'EOF'
import duckdb

conn = duckdb.connect('data_lake/bionexus.duckdb')

# View ingestion summary
print("Ingestion Summary:")
conn.execute("SELECT * FROM bronze.v_ingestion_summary").show()

# Check data quality
print("\nData Quality Check:")
conn.execute("SELECT * FROM bronze.v_data_quality_checks").show()

# Query silver layer
print("\nRefined Proteins:")
conn.execute("SELECT * FROM silver.proteins_refined LIMIT 5").show()
EOF
```

### 🛑 Stop Services

```bash
# Graceful shutdown
make down

# Full reset (⚠️  deletes all data)
make clean
```

### 📋 View Logs

```bash
# All services
make logs

# Specific service
docker-compose logs -f postgres
docker-compose logs -f neo4j
docker-compose logs -f mongodb
```

---

## Ingestion Workflow

### Step 1: Fetch Raw Data
Ingestion agents fetch from APIs → `bronze.*_raw` tables

### Step 2: Register in Audit
```sql
INSERT INTO bronze.ingestion_audit 
  (source_name, table_name, batch_id, record_count, status)
VALUES ('NCBI', 'bronze.ncbi_geo_raw', 'batch_20260321', 5000, 'success');
```

### Step 3: Refine to Silver
Use Polars/Pandas to clean and standardize:
```python
import duckdb
import polars as pl

conn = duckdb.connect('data_lake/bionexus.duckdb')

# Read raw
raw = conn.execute("SELECT * FROM bronze.ncbi_geo_raw WHERE batch_id = ?", 
                   ['batch_20260321']).df()

# Transform with Polars
df = pl.from_pandas(raw).with_columns([
    pl.col('accession_id').str.to_uppercase().alias('accession_id_norm'),
])

# Write to Silver
conn.from_df(df).insert_into('silver.ncbi_geo_refined')
```

### Step 4: Load to Production Databases
```sql
-- Load to Postgres
INSERT INTO silver.proteins (uniprot_accession, gene_name, ...)
SELECT ... FROM duckdb.silver.proteins_refined;

-- Load to Neo4j (via Cypher)
CREATE (p:Protein {uniprot_id: $id, name: $name})
```

---

## Monitoring

### Check Processing Status
```bash
# View latest ingestions
psql -h localhost -U bionexus_user -d bionexus << 'EOF'
SELECT * FROM metadata.processing_log 
ORDER BY start_time DESC LIMIT 10;
EOF
```

### Data Distribution
```bash
python3 << 'EOF'
import duckdb

conn = duckdb.connect('data_lake/bionexus.duckdb')

# Show data lake sizes
conn.execute("""
  SELECT table_name, COUNT(*) as record_count
  FROM bronze.v_data_quality_checks
  GROUP BY table_name
""").show()
EOF
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5432
lsof -i :5432

# Kill it
kill -9 <PID>

# Restart
make restart
```

### Database Won't Connect
```bash
# Check service status
make health

# View logs
docker-compose logs postgres

# Restart specific service
docker-compose restart postgres
```

### DuckDB File Corrupted
```bash
# Backup and reinitialize
mv data_lake/bionexus.duckdb data_lake/bionexus.duckdb.bak
python scripts/duckdb_lake_init.py
```

---

## Environment Variables

Edit `.env` to customize:

```env
# Database credentials
POSTGRES_PASSWORD=your_password
NEO4J_PASSWORD=your_password
MONGODB_PASSWORD=your_password

# Data lake path
DUCKDB_PATH=data_lake/bionexus.duckdb

# Batch processing
BATCH_SIZE=1000
PARQUET_COMPRESSION=snappy
```

**⚠️  Important:** Change passwords from defaults in production!

---

## Next Steps

1. **Ingest Data:** Run ingestion agents from `src/agents/`
2. **Refine Data:** Execute transformation pipelines
3. **Populate Graphs:** Load into Neo4j knowledge graph
4. **Query:** Use APIs or visualization layer

For more details: See `DOCKER_SETUP.md` and `CONTRIBUTING.md`
