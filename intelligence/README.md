# BioNexus Intelligence (FastMCP + Ollama + RAG)

This module exposes BioNexus intelligence tools over **FastMCP** and a lightweight REST bridge, and connects them to:
- **Postgres staging** (`silver.*`) for UniProt-centric evidence retrieval.
- **Local Ollama** for low-latency inference.
- **RAG snippets** from `silver.ncbi_studies` (seeded from `Lake/data_lake/silver/silver_ncbi_studies.csv`).

## Implemented MCP Tools

- `get_drug_leads(gene)`
  - Resolves gene to **UniProt ID** from `silver.proteins`.
  - Retrieves linked Reactome pathways and study snippets.
  - Adds Open Targets evidence when available.
  - Returns a grounded response with mandatory `Data Source Attribution`.

- `explain_pathway(study_id)`
  - Retrieves study metadata by GEO accession.
  - Maps candidate pathways through gene mentions + UniProt pathway links.
  - Returns pathway interpretation with mandatory `Data Source Attribution`.

## Design Notes (SOLID)

- `service.py`: use-case orchestration only.
- `repositories.py`: data access only (Postgres + Open Targets snapshot).
- `llm.py`: Ollama transport only.
- `attribution.py`: cross-cutting response policy.
- `server.py`: FastMCP wiring only.

## Model Choice for 16GB M1

Default model is `qwen2.5:3b` (`OLLAMA_MODEL`) to balance quality and memory footprint on lower-resource devices.

## Local Development (venv)

```bash
cd intelligence
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests -v
python -m bionexus_intelligence.server
```

## Docker / Compose

Prerequisite: Lake stack must already be up (for shared networks + Postgres service).

```bash
cd Lake && docker compose up -d postgres neo4j && cd ../intelligence
docker compose up --build intelligence
```

REST bridge health check:

```bash
curl http://localhost:8081/health
```

REST bridge query:

```bash
curl -X POST http://localhost:8081/api/v1/intelligence/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What leads do we have for EGFR?","gene":"EGFR"}'
```

Run tests in a container:

```bash
docker compose run --rm test
```

## Environment Variables

- `PG_DSN` Postgres DSN (defaults to Lake network service name).
- `OLLAMA_HOST` Ollama endpoint.
- `OLLAMA_MODEL` default `qwen2.5:3b`.
- `MCP_HOST`/`MCP_PORT`/`MCP_TRANSPORT` FastMCP runtime config.
- `RAG_SNIPPET_LIMIT` study snippets to inject.
- `PATHWAY_LIMIT` pathway rows to include.
- `OT_EVIDENCE_PATH` local Open Targets JSON snapshot path.
- `STUDY_CSV_PATH` CSV used to seed `silver.ncbi_studies`.

## Safety

Before seeding to staging, study summaries are de-identified (email/phone/patient-id pattern scrubbing) in `deidentify.py`.
