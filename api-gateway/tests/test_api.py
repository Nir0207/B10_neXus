import pytest
import os
import json
from typing import Any
from fastapi.testclient import TestClient
from main import app, LOG_FILE
from database import get_postgres_connection, get_neo4j_session
from schemas import IntelligenceQueryResponse

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_for_access_token():
    response = client.post("/token", data={"username": "admin", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_failure():
    response = client.post("/token", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401

def test_get_gene_unauthorized():
    response = client.get("/api/v1/genes/P12345")
    assert response.status_code == 401

def test_get_gene_authorized():
    class FakePgConnection:
        async def fetchrow(self, _query: str, uniprot_id: str) -> dict[str, str]:
            return {
                "uniprot_id": uniprot_id,
                "gene_symbol": "GENE_P12345",
                "name": "Mocked Gene",
                "description": "Mocked gene row",
                "data_source": "Postgres (Mocked)",
            }

    async def _override_postgres_connection() -> Any:
        yield FakePgConnection()

    app.dependency_overrides[get_postgres_connection] = _override_postgres_connection
    login_resp = client.post("/token", data={"username": "admin", "password": "password"})
    token = login_resp.json()["access_token"]
    
    try:
        response = client.get("/api/v1/genes/P12345", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["uniprot_id"] == "P12345"
        assert "gene_symbol" in data
    finally:
        app.dependency_overrides.pop(get_postgres_connection, None)

def test_get_discovery_graph_authorized():
    class FakeNeo4jResult:
        async def data(self) -> list[dict[str, Any]]:
            return [
                {
                    "nodes": [
                        {"id": "node1", "labels": ["Gene"], "properties": {"uniprot_id": "P12345"}},
                        {"id": "node2", "labels": ["Disease"], "properties": {"name": "Liver Cancer"}},
                        {"id": "node3", "labels": ["Medicine"], "properties": {"name": "DrugX"}},
                    ],
                    "relationships": [
                        {
                            "id": "rel1",
                            "type": "ASSOCIATED_WITH",
                            "start_node": "node1",
                            "end_node": "node2",
                            "properties": {},
                        },
                        {
                            "id": "rel2",
                            "type": "TREATS",
                            "start_node": "node3",
                            "end_node": "node2",
                            "properties": {},
                        },
                        {
                            "id": "rel3",
                            "type": "BINDS_TO",
                            "start_node": "node3",
                            "end_node": "node1",
                            "properties": {},
                        },
                    ],
                }
            ]

    class FakeNeo4jSession:
        async def run(self, _query: str, **_params: Any) -> FakeNeo4jResult:
            return FakeNeo4jResult()

    async def _override_neo4j_session() -> Any:
        yield FakeNeo4jSession()

    app.dependency_overrides[get_neo4j_session] = _override_neo4j_session
    login_resp = client.post("/token", data={"username": "admin", "password": "password"})
    token = login_resp.json()["access_token"]
    
    try:
        response = client.get("/api/v1/discovery/graph", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "relationships" in data
    finally:
        app.dependency_overrides.pop(get_neo4j_session, None)

def test_get_discovery_triplets_authorized():
    class FakeNeo4jResult:
        async def data(self) -> list[dict[str, Any]]:
            return [
                {
                    "nodes": [
                        {"id": "gene1", "labels": ["Gene"], "properties": {"uniprot_id": "P12345", "symbol": "CYP3A4"}},
                        {"id": "disease1", "labels": ["Disease"], "properties": {"name": "Liver injury"}},
                        {"id": "medicine1", "labels": ["Medicine"], "properties": {"name": "DrugX"}},
                    ],
                    "relationships": [
                        {"id": "r1", "type": "ASSOCIATED_WITH", "start_node": "gene1", "end_node": "disease1", "properties": {"score": 0.9}},
                        {"id": "r2", "type": "TREATS", "start_node": "medicine1", "end_node": "disease1", "properties": {"phase": 3}},
                    ],
                }
            ]

    class FakeNeo4jSession:
        async def run(self, _query: str, **_params: Any) -> FakeNeo4jResult:
            return FakeNeo4jResult()

    async def _override_neo4j_session() -> Any:
        yield FakeNeo4jSession()

    app.dependency_overrides[get_neo4j_session] = _override_neo4j_session
    token = client.post("/token", data={"username": "admin", "password": "password"}).json()["access_token"]

    try:
        response = client.get(
            "/api/v1/discovery/triplets?organ=liver",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"][0]["type"] == "Gene"
        assert any(edge["relationship"] == "TREATS" for edge in data["edges"])
    finally:
        app.dependency_overrides.pop(get_neo4j_session, None)

def test_audit_log_created():
    client.get("/")
    
    assert os.path.exists(LOG_FILE)
    
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
        assert len(lines) > 0
        
        last_log = json.loads(lines[-1].strip())
        assert "Timestamp" in last_log
        assert "User_ID" in last_log
        assert "Endpoint" in last_log
        assert "Request_Hash" in last_log
        assert "Status_Code" in last_log
        assert last_log["Endpoint"] == "/"


def test_query_intelligence_authorized(monkeypatch):
    async def _fake_query(_payload):
        return IntelligenceQueryResponse(
            reply="EGFR fallback reply",
            mode="drug_leads",
            resolved_entity="EGFR",
            sources=["Source: UniProt"],
        )

    monkeypatch.setattr("router._query_intelligence_service", _fake_query)
    token = client.post("/token", data={"username": "admin", "password": "password"}).json()["access_token"]

    response = client.post(
        "/api/v1/intelligence/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "What leads do we have for EGFR?", "gene": "EGFR"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "drug_leads"
    assert body["resolved_entity"] == "EGFR"
