Here is a comprehensive `CONTRIBUTING.md` specifically designed for your "Hybrid AI" workflow. This ensures that whether you are using **GitHub Copilot** (for speed) or **Antigravity** (for architecture), your Git history stays clean and your biological data remains de-identified.

---

# 🤝 Contributing to BioNexus

Welcome to the **BioNexus** development team. Because this project uses a hybrid AI workflow (GitHub Copilot + Antigravity), we follow a strict "Architect-first" contribution model to ensure data integrity and budget efficiency.

## 🛠 The Hybrid AI Workflow

To stay within the Antigravity budget while maintaining high code quality, follow this 3-step cycle:

1.  **Plan (Antigravity):** Use Antigravity to design the "Technical Spec" or "Data Schema." Do not let it write the full code yet.
2.  **Build (GitHub Copilot):** Take the spec into VS Code and use Copilot to generate the boilerplate, unit tests, and API calls.
3.  **Review (Antigravity):** Paste the finished code back into Antigravity for a "Pharma-grade" audit.

---

## 🌿 Branching Strategy

We use a modified **Git Flow** to track AI-generated changes:

* **`main`**: Production-ready, stable code. Only merged after a full manual audit.
* **`develop`**: The integration branch for new features.
* **`feat/ai-[feature-name]`**: Temporary branches for AI-generated code. 
    * *Example:* `feat/ai-uniprot-gatherer`

### Commit Message Convention
We use prefixes to identify which tool generated the code:
* `🤖 [Copilot]`: For boilerplate, CSS, or basic logic.
* `🧠 [Antigravity]`: For architectural changes or complex bio-logic.
* `👤 [Manual]`: For human-written fixes or configuration changes.

---

## 🧪 Data Contribution Rules

**CRITICAL: De-identification & GxP Compliance**
Since BioNexus mimics a regulated environment, follow these rules:

1.  **No PII:** Never commit real patient data. Use the `scripts/generate_mock_data.py` tool for development.
2.  **Data Lineage:** Every new "Gatherer" must include a `metadata.json` describing the source (NCBI, UniProt, etc.) and the date of retrieval.
3.  **Refinery Verification:** Any change to the `refinery/` logic must pass the `pytest` suite to ensure no "Gene Mapping" errors were introduced.

---

## 🚦 Pull Request (PR) Checklist

Before submitting a PR, ensure:
- [ ] Code was reviewed by **Antigravity** for architectural consistency.
- [ ] Unit tests (written by **Copilot**) cover at least 80% of the logic.
- [ ] No hardcoded API keys or local paths are present.
- [ ] Documentation in `/docs` has been updated to reflect new data links (e.g., a new BioGRID connection).

---

## 💰 Budget Management (Local Development)

* **Dry Runs:** Always run gatherers with a `--limit 5` flag first to ensure the API call is correct before pulling the full dataset.
* **Artifacts:** Clean up Antigravity "Artifacts" regularly to keep the workspace responsive.
* **Ollama:** Ensure your local Ollama instance is running `BioMistral` or `Phi-4` before testing the Intelligence layer.

---

### **Would you like me to generate the first "Refinery" script template now so you can test this workflow in VS Code?**