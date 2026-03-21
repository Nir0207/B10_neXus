from __future__ import annotations

from bionexus_intelligence.server import MCPToolAdapter


class _FakeService:
    def get_drug_leads(self, gene: str) -> str:
        return f"drug:{gene}"

    def explain_pathway(self, study_id: str) -> str:
        return f"pathway:{study_id}"

    def render_visual_report(self, *, prompt: str, disease: str):
        class _Report:
            chart_type = "bar"
            title = "title"
            disease_id = "alzheimers-disease"
            disease_name = "Alzheimer's disease"
            x_key = "gene_symbol"
            y_key = "association_score"
            datasets = [{"gene_symbol": "APP", "association_score": 0.91}]
            clinical_summary = "summary"

        return _Report()


def test_mcp_tool_adapter_delegates_to_service() -> None:
    adapter = MCPToolAdapter(_FakeService())

    assert adapter.get_drug_leads("BRCA1") == "drug:BRCA1"
    assert adapter.explain_pathway("GSE123") == "pathway:GSE123"
    assert '"chart_type": "bar"' in adapter.render_visual_report("Show gene trends", "Alzheimer's disease")
