from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import main
from database import get_neo4j_session


class FakeNeo4jResult:
    async def data(self) -> list[dict[str, Any]]:
        return [
            {
                "nodes": [
                    {"id": "gene_1", "labels": ["Gene"], "properties": {"uniprot_id": "P12345"}},
                    {"id": "disease_1", "labels": ["Disease"], "properties": {"name": "NASH"}},
                ],
                "relationships": [
                    {
                        "id": "rel_1",
                        "type": "ASSOCIATED_WITH",
                        "start_node": "gene_1",
                        "end_node": "disease_1",
                        "properties": {"evidence_score": 0.92},
                    }
                ],
            }
        ]


class FakeNeo4jSession:
    async def run(self, _query: str) -> FakeNeo4jResult:
        return FakeNeo4jResult()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def _noop() -> None:
        return None

    monkeypatch.setattr(main, "init_db", _noop)
    monkeypatch.setattr(main, "close_db", _noop)
    main.app.state.audit_log_file = str(tmp_path / "audit.log")
    main.app.dependency_overrides.clear()

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


def _login_and_get_token(client: TestClient) -> str:
    response = client.post("/token", data={"username": "admin", "password": "password"})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def test_unauthorized_request_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/genes/P12345")
    assert response.status_code == 401


def test_mocked_neo4j_graph_retrieval_success(client: TestClient) -> None:
    async def _override_neo4j_session() -> Any:
        yield FakeNeo4jSession()

    main.app.dependency_overrides[get_neo4j_session] = _override_neo4j_session
    token = _login_and_get_token(client)

    response = client.get(
        "/api/v1/discovery/graph",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["nodes"]) == 2
    assert len(payload["relationships"]) == 1
    assert payload["nodes"][0]["properties"]["uniprot_id"] == "P12345"


def test_audit_middleware_logs_transaction(client: TestClient) -> None:
    token = _login_and_get_token(client)
    response = client.get("/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    audit_log_path = Path(main.app.state.audit_log_file)
    assert audit_log_path.exists()

    lines = audit_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    last_entry = json.loads(lines[-1])

    assert last_entry["Endpoint"] == "/"
    assert last_entry["Status_Code"] == 200
    assert last_entry["User_ID"] == "admin"
    assert len(last_entry["Request_Hash"]) == 64
