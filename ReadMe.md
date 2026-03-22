# 🧬 BioNexus: Local-First Multi-Omics Intelligence

**BioNexus** is a production-grade, local-only pharmaceutical discovery platform. It automates the ingestion, refinement, and synthesis of global biological data to identify links between **Organs, Genes, Diseases, and Medicines**.

Built for the 2026 agentic era, BioNexus utilizes a tiered data refinery and a local "Intelligence Swarm" to provide drug discovery insights without cloud costs or data privacy risks.

---

## 🏗 System Architecture: The Data Factory

BioNexus operates as a **Med-Data Lakehouse**, moving data through four distinct maturity stages:

1.  **The Gatherers (Ingestion):** Autonomous Python agents poke open-source APIs (NCBI, Open Targets, UniProt, etc.) to fetch raw biological metadata.
2.  **The Lake (Bronze):** Raw JSON/XML responses are stored as immutable, partitioned **Parquet** files using **DuckDB**.
3.  **The Refinery (Silver):** High-performance **Polars** scripts clean, standardize (HGNC/UniProt mapping), and de-duplicate data.
4.  **The Staging (Gold):** Refined knowledge is loaded into **Postgres (pgvector)** for structured search and **Neo4j** for complex relationship mapping.



---

## 🛠 Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | **Docker / Antigravity** | Containerized microservices & Agentic management. |
| **Data Lake** | **DuckDB / Parquet** | High-speed local analytical storage. |
| **Databases** | **Postgres & Neo4j** | Relational metadata + Biological Knowledge Graph. |
| **Telemetry/Auth** | **MongoDB + GraphQL** | User accounts, admin flags, and portal analytics. |
| **Observability** | **OpenObserve + OpenTelemetry** | Local-first logs, traces, error events, and browser RUM. |
| **Processing** | **Python (Polars / FastAPI)** | Heavy-duty bio-informatic refining. |
| **AI Brain** | **Ollama / MCP / SLMs** | Local LLMs (BioMistral/Phi-4) via Model Context Protocol. |
| **UI/UX** | **Next.js / D3.js** | Dense, lab-grade scientific visualizations. |

---

## 🧪 Integrated Data Sources

BioNexus synthesizes data from the world's leading open biological repositories:
* **NCBI (GEO/PubMed):** Clinical studies and gene expression profiles.
* **Open Targets:** Evidence-based drug-target-disease associations.
* **UniProt:** Comprehensive protein sequence and functional information.
* **Reactome:** Human biological pathway mapping.
* **BioGRID:** Protein-Protein Interaction (PPI) networks.
* **ChEMBL:** Bioactive molecules and drug-like property data.

---

## 🚀 Execution Guide (Step-by-Step)

### 1. Environment Setup
Clone the repository and spin up the shared data infrastructure:
```bash
cd Lake && docker compose up -d
```
This initializes Postgres, Neo4j, and MongoDB for the local platform.

### 2. Start the Observability Stack
Launch the decoupled `/ops` stack in a separate shell:
```bash
./START_OPS.sh
```
This starts:
- `bionexus-openobserve`
- `bionexus-otel-collector`

OpenObserve is available at `http://localhost:5080`.

Default bootstrap login:
- Email: `root@bionexus.local`
- Password: `BioNexusOps123!`
- Organization: `default`

Health check:
```bash
python ops/check_health.py
```

Seed the BioNexus dashboard and direct portal links:
```bash
python ops/bootstrap_openobserve_assets.py
```

### 3. Run the Gatherers
Trigger the ingestion agents to populate the Lake:
```bash
docker compose -f gatherers/docker-compose.yml up -d --build gatherers
```

### 4. Refine the Data
Transform raw Lake data into the Staging Graph:
```bash
docker compose -f refineries/docker-compose.yml up --build pipeline
```

### 5. Launch the Brain
Start the FastMCP server to allow your local LLM to interact with the refined data:
```bash
docker compose -f intelligence/docker-compose.yml up -d --build intelligence
```

### 6. Launch the APIs and UI
```bash
cd telemetry && docker compose up -d --build
docker compose -f api-gateway/compose.yaml up -d --build api-gateway
docker compose -f ui-portal/docker-compose.yml up -d --build ui-portal
```

### 7. Access the UI
Open your browser to `http://localhost:3000` to explore the portal. The `/telemetry` route is the BioNexus admin analytics page and is separate from the OpenObserve ops portal.

## Observability Guide

The application emits service logs, FastAPI error events, gatherer/refinery logs, and browser RUM into OpenObserve through the local OTel collector.

### How to Read Logs in the OpenObserve Portal

1. Open `http://localhost:5080`.
2. Sign in with the OpenObserve credentials above.
3. Set the organization to `default`.
4. Open the seeded dashboard `BioNexus Ops` from `Dashboards`, or open `Logs`.
5. Select the stream `bionexus_app`.
6. Set a recent time range such as `Last 15 minutes`.
7. Use either the search bar or SQL mode.

Direct preset URL:
`http://localhost:5080/web/logs?stream_type=logs&stream=bionexus_app&period=15m&refresh=0&fn_editor=false&defined_schemas=user_defined_schema&org_identifier=default&quick_mode=false&show_histogram=true&logs_visualize_toggle=logs`

Useful queries:

```sql
SELECT * FROM "bionexus_app"
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE service_name = 'api-gateway'
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE severity = 'ERROR'
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE gene_context = 'P04637'
ORDER BY _timestamp DESC
LIMIT 50
```

### How to Read Browser RUM

There are two useful views:

- `RUM` in OpenObserve for browser-oriented exploration.
- `Logs` with `rum_*` fields when you want raw records.

Example SQL:

```sql
SELECT * FROM "bionexus_app"
WHERE rum_metric_name IS NOT NULL
ORDER BY _timestamp DESC
LIMIT 50
```

```sql
SELECT * FROM "bionexus_app"
WHERE service_name = 'api-gateway'
  AND rum_metric_name IS NOT NULL
ORDER BY _timestamp DESC
LIMIT 50
```

### Query Logs Without the Portal

Python client:

```python
from ops.openobserve_client import OpenObserveClient

client = OpenObserveClient()
result = client.query_logs('SELECT * FROM "bionexus_app" ORDER BY _timestamp DESC LIMIT 10')
print(result)
```

MCP tool:

```text
query_ops_logs('SELECT * FROM "bionexus_app" WHERE severity = ''ERROR'' ORDER BY _timestamp DESC LIMIT 20')
```

### OpenObserve User Management

There are three supported paths depending on what you need:

1. Bootstrap root user
   The initial admin user is created from `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD` in `ops/docker-compose.ops.yml` the first time the volume is initialized.
2. Portal-managed users
   In OpenObserve, open `IAM` -> `Users` -> `New user` to create additional human users.
3. Service accounts
   In OpenObserve, open `IAM` -> `Service Accounts` when you need machine credentials instead of a human login.

API example for creating a user from the command line:

```bash
curl -X POST "http://localhost:5080/api/default/users" \
  -H "Authorization: Basic $(printf 'root@bionexus.local:BioNexusOps123!' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ops-reader@bionexus.local",
    "password": "ChangeMe123!",
    "first_name": "Ops",
    "last_name": "Reader",
    "role": "user"
  }'
```

If you change the bootstrap root credentials after first startup, the existing `openobserve_data` volume will keep the old account. Update users from the portal or API instead, or recreate the volume if you intentionally want a clean reset.

For the detailed ops runbook, see [`ops/README.md`](ops/README.md).

## Container Runtime Guide

### First-Time Startup for a Fresh Clone

Run these in order for a new developer machine or after wiping Docker volumes:

1. Core data services
   ```bash
   cd Lake
   docker compose up -d
   ```
   Starts:
   - `bionexus-postgres`
   - `bionexus-neo4j`
   - `bionexus-mongodb`
   - `bionexus-refinery`

2. Observability stack
   ```bash
   cd ..
   ./START_OPS.sh
   ```
   Starts:
   - `bionexus-openobserve`
   - `bionexus-otel-collector`

3. Auth and telemetry backend
   ```bash
   cd telemetry
   docker compose up -d --build
   ```
   Starts:
   - `bionexus-telemetry-api`

4. Main API
   ```bash
   cd ../api-gateway
   docker compose -f compose.yaml up -d --build api-gateway
   ```
   Starts:
   - `bionexus-api-gateway`

5. Web UI
   ```bash
   cd ../ui-portal
   docker compose up -d --build
   ```
   Starts:
   - `ui-portal-ui-portal-1`

6. Optional AI stack
   Run this only if you need MCP or AI-driven features:
   ```bash
   cd ../intelligence
   docker compose up -d --build intelligence
   ```
   Starts:
   - `bionexus-intelligence-mcp`
   - `bionexus-ollama`
   - one-shot helper containers such as the model puller and DB probe

### Containers to Keep Running All the Time

For normal portal usage after startup, keep these running:

- `bionexus-postgres`
  Required for structured reads and gateway-backed analytics.
- `bionexus-neo4j`
  Required for discovery graph and pathway views.
- `bionexus-mongodb`
  Required for login, user records, admin flags, and telemetry metadata.
- `bionexus-telemetry-api`
  Required for auth, registration, session hydration, and the admin telemetry page.
- `bionexus-api-gateway`
  Required for the main REST APIs consumed by the UI.
- `ui-portal-ui-portal-1`
  Required for the web app itself.

Recommended to keep running during development:

- `bionexus-openobserve`
  Required if you want the ops portal, logs, traces, and RUM.
- `bionexus-otel-collector`
  Required for collecting OTLP logs and traces into OpenObserve.

Keep these running only when you need AI features:

- `bionexus-intelligence-mcp`
  Required for MCP tools and intelligence routes.
- `bionexus-ollama`
  Required for local model inference used by the intelligence service.

### Containers to Run On Demand

These are not required just to browse the product:

- `bionexus-gatherers`
  Run when you want to ingest fresh source data into `Lake/data_lake/raw`.
  ```bash
  docker compose -f gatherers/docker-compose.yml up -d --build gatherers
  ```
- `bionexus-refinery-pipeline`
  Run when you want to process raw data into silver/staging outputs.
  ```bash
  docker compose -f refineries/docker-compose.yml up --build pipeline
  ```
- `bionexus-refinery`
  This is the long-lived helper container from the Lake stack. It is useful for ETL work, but not required for day-to-day portal usage.

### Short Version for New Users

If the goal is simply "clone the repo and use the BioNexus portal locally", the minimum startup sequence is:

1. `cd Lake && docker compose up -d`
2. `cd .. && ./START_OPS.sh`
3. `cd telemetry && docker compose up -d --build`
4. `cd ../api-gateway && docker compose -f compose.yaml up -d --build api-gateway`
5. `cd ../ui-portal && docker compose up -d --build`

After that:

- BioNexus UI: `http://localhost:3000`
- OpenObserve: `http://localhost:5080`
- API Gateway: `http://localhost:8000`
- Telemetry API: `http://localhost:4100`

### Environment Files New Users Must Create

Create these files before the first full startup:

1. Root env file
   Copy [`/.env.example`](/BioNexus/.env.example) to `.env`
2. Refinery env file
   Copy [`refineries/.env.example`](/BioNexus/refineries/.env.example) to `refineries/.env`

### Root `.env` Keys

Minimum keys a new user should set in `.env`:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `MONGODB_USER`
- `MONGODB_PASSWORD`
- `MONGODB_DATABASE`
- `TELEMETRY_ADMIN_USERNAME`
- `TELEMETRY_ADMIN_PASSWORD`
- `TELEMETRY_ADMIN_EMAIL`
- `TELEMETRY_ADMIN_FULL_NAME`
- `SECRET_KEY`
- `JWT_ISSUER`
- `JWT_AUDIENCE`

Useful non-secret root `.env` keys:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `NEO4J_HOST`
- `NEO4J_BOLT_PORT`
- `NEO4J_HTTP_PORT`
- `MONGODB_HOST`
- `MONGODB_PORT`
- `TELEMETRY_PORT`
- `TELEMETRY_GRAPHQL_URL`
- `NEXT_PUBLIC_TELEMETRY_API_URL`
- `DUCKDB_PATH`
- `LAKE_DIRECTORY`
- `SILVER_DIRECTORY`
- `DEBUG`
- `LOG_LEVEL`
- `ENV`

### `refineries/.env` Keys

Required keys:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `NEO4J_PASSWORD`

Optional keys:

- `FORCE`
- `SKIP_POSTGRES`
- `SKIP_NEO4J`

### Environment Variables Already Bootstrapped by Compose

New users do not need to create separate env files for these unless they want to override defaults:

- OpenObserve / ops:
  - `OPENOBSERVE_BASE_URL`
  - `OPENOBSERVE_ORG`
  - `OPENOBSERVE_USERNAME`
  - `OPENOBSERVE_PASSWORD`
  - `OPENOBSERVE_LOG_STREAM`
  - `OPENOBSERVE_DASHBOARD_TITLE`
  - `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT`
- UI:
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_BIONEXUS_API_TOKEN`
- Intelligence:
  - `PG_DSN`
  - `OLLAMA_HOST`
  - `OLLAMA_MODEL`
  - `MCP_HOST`
  - `MCP_PORT`
  - `MCP_TRANSPORT`

---

## 🧠 Intelligence Layer: "The Swarm"

BioNexus does not rely on a single large LLM. It uses a **Task-Specific Routing** system:
* **Router (Phi-3.5 Mini):** Analyzes user intent and selects the correct tool.
* **Researcher (RAG + pgvector):** Fetches relevant study snippets from the local vector DB.
* **Analyst (Neo4j + BioMistral):** Traverses the knowledge graph to explain *why* a drug-gene link exists.