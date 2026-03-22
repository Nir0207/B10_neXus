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
| **Telemetry/Auth** | **MongoDB + GraphQL** | User accounts, admin flags, and client telemetry analytics. |
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
Clone the repository and spin up the core infrastructure:
```bash
cd Lake && docker compose up -d
```
*This initializes Postgres, Neo4j, and MongoDB for the local platform.*

### 2. Run the Gatherers
Trigger the ingestion agents to populate the Lake:
```bash
python ./gatherers/ncbi_fetcher.py --organ liver
python ./gatherers/opentargets_sync.py
```

### 3. Refine the Data
Transform raw Lake data into the Staging Graph:
```bash
python ./refinery/standardize_mapping.py
python ./refinery/load_neo4j.py
```

### 4. Launch the Brain
Start the **FastMCP** server to allow your local LLM to interact with the refined data:
```bash
mcp install ./intelligence/bionexus_mcp.py
ollama run biomistral
```

### 5. Launch the APIs and UI
```bash
cd telemetry && docker compose up -d --build
cd api-gateway && docker compose up -d --build
cd ui-portal && docker compose up -d --build
```

### 6. Access the UI
Open your browser to `http://localhost:3000` to explore the portal. The `/telemetry` route is available only to users with `isAdmin=true`.

## Container Runtime Guide

### First-time startup order

Run these once after a fresh clone, after Docker volume cleanup, or after infrastructure changes:

1. `Lake/docker-compose.yml`
   Starts the shared data-plane containers:
   `bionexus-postgres`, `bionexus-neo4j`, `bionexus-mongodb`, `bionexus-refinery`
2. `telemetry/docker-compose.yml`
   Starts `bionexus-telemetry-api`
3. `api-gateway/compose.yaml`
   Starts `bionexus-api-gateway`
4. `ui-portal/docker-compose.yml`
   Starts `ui-portal-ui-portal-1`

### Containers that must be running all the time

For the application to be functional in normal portal usage, these containers should stay up:

- `bionexus-mongodb`
  Required for Mongo-backed auth, user records, admin flags, and telemetry events.
- `bionexus-telemetry-api`
  Required for login, registration, session hydration, admin checks, and telemetry dashboard data.
- `bionexus-api-gateway`
  Required for the explorer, pathways, trials, and analytics REST APIs.
- `ui-portal-ui-portal-1`
  Required for the web UI itself.
- `bionexus-postgres`
  Required for gateway-backed analytics and structured data reads.
- `bionexus-neo4j`
  Required for discovery graph and pathway/relationship views.

### Containers that are helpful but not required all the time

- `bionexus-refinery`
  Keep this up when you are running ETL/refinery jobs; it is not required just to browse the UI.

---

## 🧠 Intelligence Layer: "The Swarm"

BioNexus does not rely on a single large LLM. It uses a **Task-Specific Routing** system:
* **Router (Phi-3.5 Mini):** Analyzes user intent and selects the correct tool.
* **Researcher (RAG + pgvector):** Fetches relevant study snippets from the local vector DB.
* **Analyst (Neo4j + BioMistral):** Traverses the knowledge graph to explain *why* a drug-gene link exists.
