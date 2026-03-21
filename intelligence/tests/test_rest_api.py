from __future__ import annotations

from fastapi.testclient import TestClient

from bionexus_intelligence.rest_api import create_app


class _FakeService:
    def initialize(self, _path) -> int:
        return 0

    def get_drug_leads(self, gene: str) -> str:
        return f"lead:{gene}\n\nData Source Attribution: Source: UniProt; Source: Open Targets"

    def explain_gene(self, gene: str) -> str:
        return f"gene:{gene}\n\nData Source Attribution: Source: UniProt"

    def explain_pathway(self, study_id: str) -> str:
        return f"pathway:{study_id}\n\nData Source Attribution: Source: NCBI GEO"


def test_query_routes_gene_requests(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "What leads do we have for EGFR?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "drug_leads"
    assert body["resolved_entity"] == "EGFR"
    assert body["sources"] == ["Source: UniProt", "Source: Open Targets"]


def test_query_routes_study_requests(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "Explain pathway impact for GSE12345"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "pathway"
    assert body["resolved_entity"] == "GSE12345"


def test_query_routes_gene_overview_requests(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "What is GRIN2B?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "gene_overview"
    assert body["resolved_entity"] == "GRIN2B"


def test_query_falls_back_to_context_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "Help me", "organ": "brain", "gene": "EGFR"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "drug_leads"
    assert body["resolved_entity"] == "EGFR"
