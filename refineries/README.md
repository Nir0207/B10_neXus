# BioNexus Refinery  — Silver Layer

Polars-based microservice that transforms raw Bronze-layer JSON into
query-ready Silver-layer tables in Postgres and Neo4j.

## Medallion position

```
Bronze  (raw/)          ──►  refineries/  ──►  Silver (Postgres / Neo4j)
  UniProt JSON                                    silver.proteins
  NCBI GEO JSON                                   silver.genes
                                                  silver.pathways
                                                  silver.protein_pathway
                                                  :Gene -[:ENCODES]-> :Protein
                                                  :Protein -[:INVOLVED_IN]-> :Pathway
```

## Mapping chain

```
Gene Symbol  ──►  UniProt ID (primaryAccession)
                       │
                       └──►  Reactome Pathway IDs (from embedded xrefs)
```

Reactome pathway data is read **directly from the UniProt JSON**
(`uniProtKBCrossReferences[database=Reactome]`) — no extra API calls required.

## Quickstart (Docker — recommended)

```bash
# 1. Start the Lake stack first (Postgres + Neo4j must be healthy)
cd ../Lake && docker compose up -d && cd ../refineries

# 2. Copy env file and edit passwords if needed
cp .env.example .env

# 3. Run the full ETL pipeline (one-shot container, exits 0 on success)
docker compose up pipeline

# 4. Force re-process all files (ignore idempotency manifest)
docker compose run --rm pipeline run_pipeline.py --force

# 5. Skip DB steps — write Silver CSVs only
docker compose run --rm pipeline run_pipeline.py --skip-postgres --skip-neo4j

# 6. Run pytest (no DB required — all DB calls are mocked)
docker compose run --rm test

# 7. Rebuild images after code changes
docker compose up --build pipeline
```

## Local development (without Docker)

```bash
cd refineries
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
python run_pipeline.py --skip-postgres --skip-neo4j   # CSV-only
```

## Output CSVs  (`Lake/data_lake/silver/`)

| File | Contents |
|------|----------|
| `silver_proteins.csv` | One row per UniProt entry; ready for `silver.proteins` upsert |
| `silver_gene_symbol_map.csv` | Gene Symbol → UniProt ID lookup |
| `silver_reactome_map.csv` | UniProt ID → Reactome Pathway mapping |
| `silver_ncbi_studies.csv` | One row per GEO study |

## Idempotency

Each processed file is fingerprinted by MD5 hash and recorded in
`.processed_manifest.json`.  Re-running the pipeline skips unchanged
files automatically.

When one or more files change, the refinery rebuilds a **full Silver CSV
snapshot** from all raw files and updates the manifest only after CSV
writes succeed, preventing partial-state drift. Pass `--force` to
override idempotency and re-process everything.

## Environment variables (`.env`)

```
PG_DSN=postgresql://bionexus_user:bionexus_pass@localhost:5432/bionexus
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=bionexus_neo4j
```

## Module overview

| Module | Responsibility |
|--------|---------------|
| `config.py` | Paths, DB DSNs, manifest path |
| `idempotency.py` | MD5-based file processing guard |
| `refine_uniprot.py` | UniProt JSON → 3 Silver CSVs |
| `refine_ncbi.py` | NCBI GEO JSON → Silver CSV |
| `load_postgres.py` | Upsert Silver CSVs into Postgres (`silver.*`) |
| `load_neo4j.py` | Merge nodes/edges into Neo4j |
| `run_pipeline.py` | Orchestrates all four steps |
