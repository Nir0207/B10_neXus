# 🧬 BioNexus Docker Compose & DuckDB Lake Setup

## Quick Start

### 1. Start Services

```bash
# Start all containers (Postgres, Neo4j, MongoDB)
docker-compose up -d

# Verify services are healthy
docker-compose ps

# View logs
docker-compose logs -f
```

### 2. Initialize DuckDB Lake

```bash
# Install dependencies
pip install -r requirements.txt

# Run lake initializer
python scripts/duckdb_lake_init.py
```

The initializer will:
- ✓ Create Bronze layer for raw ingestion
- ✓ Create Silver layer for refined data
- ✓ Setup Parquet registry
- ✓ Create data quality views
- ✓ Configure ingestion audit tables

---

## Service Details

### 📊 Postgres (pgvector)
- **Port:** 5432
- **Database:** `bionexus`
- **User:** `bionexus_user`
- **Features:** pgvector extension (384-dim embeddings)
- **Init Script:** `init-scripts/postgres-init.sql`

**Connection:**
```bash
psql -h localhost -U bionexus_user -d bionexus
```

**Schema:**
- `silver.*` - Refined biological entities (proteins, genes, diseases, compounds)
- `metadata.*` - Data lineage and processing metadata

### 🔗 Neo4j
- **Port (Bolt):** 7687
- **Port (HTTP):** 7474
- **User:** `neo4j`
- **Dashboard:** http://localhost:7474/browser
- **Init Script:** `init-scripts/neo4j-init.cypher`

**Connection:**
```bash
# Browser
Open http://localhost:7474

# Cypher Shell
docker-compose exec neo4j bin/cypher-shell -u neo4j -p bionexus_dev_password
```

**Graph Model:**
- Nodes: Gene, Protein, Disease, Compound
- Relationships: ENCODES, TARGETS, ASSOCIATED_WITH, INTERACTS_WITH

### 🍃 MongoDB
- **Port:** 27017
- **Admin User:** `bionexus_admin`
- **Database:** `bionexus`
- **Init Script:** `init-scripts/mongodb-init.js`

**Connection:**
```bash
mongosh -u bionexus_admin -p <password> --authenticationDatabase admin --host localhost:27017
```

**Collections:**
- `raw_ingestions` - Raw API responses
- `ingestion_metadata` - Batch processing metadata
- `data_lineage` - Data transformation tracking
- `api_responses_cache` - Cached external API responses (30-day TTL)

### 🦆 DuckDB Lake
- **Path:** `data_lake/bionexus.duckdb`
- **Bronze Schema:** Raw ingestion tables (partitioned by source)
- **Silver Schema:** Refined/deduplicated data
- **Parquet Format:** Snappy compression, date-partitioned

**Layer Structure:**
```
Bronze (Raw) → [ETL] → Silver (Refined) → [Load] → Postgres/Neo4j
```

---

## Common Tasks

### Health Checks
```bash
# Check all services
docker-compose ps

# Test Postgres
docker-compose exec postgres pg_isready -U bionexus_user

# Test Neo4j
curl http://localhost:7474/db/neo4j/label/

# Test MongoDB
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f neo4j
docker-compose logs -f mongodb
```

### Reset Services
```bash
# Stop and remove volumes (⚠️ DATA LOSS)
docker-compose down -v

# Reinitialize
docker-compose up -d
python scripts/duckdb_lake_init.py
```

### Access DuckDB
```bash
# Interactive DuckDB shell
python -c "import duckdb; conn = duckdb.connect('data_lake/bionexus.duckdb'); conn.execute('SELECT * FROM bronze.v_ingestion_summary').show()"
```

---

## Data Ingestion Pipeline

### Adding New Data Source

1. **Define table in `bronze` schema** (in `duckdb_lake_init.py`)
2. **Create ingestion agent** (fetches raw data from API)
3. **Register in audit table:**
   ```sql
   INSERT INTO bronze.ingestion_audit (source_name, table_name, batch_id, record_count, status)
   VALUES ('SOURCE', 'bronze.source_raw', 'batch_001', 5000, 'processing');
   ```
4. **Load into Parquet:** `INSERT INTO bronze.source_raw SELECT * FROM ...`
5. **Refine to Silver:** Transform and deduplicate

---

## troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :5432

# Kill process
kill -9 <PID>
```

### Database Won't Start
```bash
# Check logs
docker-compose logs <service>

# Restart
docker-compose restart <service>
```

### Permission Issues
```bash
# Ensure permissions on data_lake directory
chmod 755 data_lake
chmod 644 data_lake/bionexus.duckdb
```

---

## Environment Variables

Key variables can be customized in `.env`:

```env
POSTGRES_PASSWORD=your_password
NEO4J_PASSWORD=your_password
MONGODB_PASSWORD=your_password
DUCKDB_PATH=data_lake/bionexus.duckdb
```

**Note:** Change passwords from defaults in production!

---

## Next Steps

After initialization:
1. Run ingestion agents to populate Bronze layer
2. Execute refinery pipelines to populate Silver layer
3. Load refined data into Postgres/Neo4j
4. Query through APIs or viz layer

For more info: see `CONTRIBUTING.md` and `Mission Briefing.md`
