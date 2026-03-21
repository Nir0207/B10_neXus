from __future__ import annotations

from fastapi.testclient import TestClient

from bionexus_intelligence.models import VisualReport
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

    def summarize_organ_context(
        self,
        *,
        organ: str,
        question: str,
        history=None,
        disease=None,
        medicine=None,
        gene=None,
    ) -> str:
        return f"organ:{organ}:{question}\n\nData Source Attribution: Source: Organ Atlas"

    def summarize_discovery_context(
        self,
        *,
        question: str,
        history=None,
        organ=None,
        gene=None,
        uniprot_id=None,
        disease=None,
        medicine=None,
    ) -> str:
        return f"context:{organ}:{gene}:{question}\n\nData Source Attribution: Source: Discovery Graph"

    def render_visual_report(self, *, prompt: str, disease: str) -> VisualReport:
        return VisualReport(
            chart_type="bar",
            title=f"{disease} Gene Distribution",
            disease_id="alzheimers-disease",
            disease_name="Alzheimer's disease",
            x_key="gene_symbol",
            y_key="association_score",
            datasets=[{"gene_symbol": "APP", "association_score": 0.91}],
            clinical_summary="Visual summary",
        )


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


def test_query_routes_organ_overview_requests(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "What is the focus of this organ atlas?", "organ": "brain"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "organ_overview"
    assert body["resolved_entity"] == "brain"


def test_query_routes_contextual_followups(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={
            "prompt": "What should we test next?",
            "organ": "liver",
            "gene": "EGFR",
            "disease": "Liver Neoplasms",
            "medicine": "Gefitinib",
            "history": [{"role": "user", "text": "What leads do we have for EGFR?"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "discovery_context"
    assert body["resolved_entity"] == "EGFR"
    assert body["sources"] == ["Source: Discovery Graph"]


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
    assert body["mode"] == "discovery_context"
    assert body["resolved_entity"] == "EGFR"


def test_query_routes_visual_trend_requests(monkeypatch) -> None:
    monkeypatch.setattr(
        "bionexus_intelligence.rest_api.create_intelligence_service",
        lambda _settings: _FakeService(),
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/v1/intelligence/query",
        json={"prompt": "Analyze the rise of Alzheimer's genes", "disease": "Alzheimer's disease"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "visual_report"
    assert body["visual_payload"]["chart_type"] == "bar"
    assert body["visual_payload"]["datasets"][0]["gene_symbol"] == "APP"
