This `README.md` is designed to be the "Grand Map" for your project. It’s structured to satisfy both a Lead Scientist and a Senior Developer, emphasizing the **Med-Data Lakehouse** architecture and your **Local-First AI** strategy.

---

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
docker-compose up -d
```
*This initializes Postgres, Neo4j, MongoDB, and the Ollama instance.*

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

### 5. Access the UI
Open your browser to `http://localhost:3000` to explore the **Organ-to-Medicine** visualizer.

---

## 🧠 Intelligence Layer: "The Swarm"

BioNexus does not rely on a single large LLM. It uses a **Task-Specific Routing** system:
* **Router (Phi-3.5 Mini):** Analyzes user intent and selects the correct tool.
* **Researcher (RAG + pgvector):** Fetches relevant study snippets from the local vector DB.
* **Analyst (Neo4j + BioMistral):** Traverses the knowledge graph to explain *why* a drug-gene link exists.
