from __future__ import annotations

from bionexus_intelligence.server import MCPToolAdapter


class _FakeService:
    def get_drug_leads(self, gene: str) -> str:
        return f"drug:{gene}"

    def explain_pathway(self, study_id: str) -> str:
        return f"pathway:{study_id}"


def test_mcp_tool_adapter_delegates_to_service() -> None:
    adapter = MCPToolAdapter(_FakeService())

    assert adapter.get_drug_leads("BRCA1") == "drug:BRCA1"
    assert adapter.explain_pathway("GSE123") == "pathway:GSE123"
