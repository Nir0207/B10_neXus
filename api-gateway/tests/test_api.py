import pytest
import os
import json
from typing import Any
from fastapi.testclient import TestClient
from auth import get_password_hash
from main import app, LOG_FILE
from database import get_postgres_connection, get_neo4j_session
from schemas import IntelligenceQueryResponse

client = TestClient(app)


class FakeUserPgConnection:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, str | None]] = {}

    async def fetchrow(self, query: str, *args: object) -> dict[str, str | None] | None:
        normalized_query = " ".join(query.split())

        if "FROM app_users WHERE username = $1" in normalized_query:
            username = str(args[0]).lower()
            user = self.users.get(username)
            if user is None:
                return None
            return {
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "hashed_password": user["hashed_password"],
            }

        if "FROM app_users WHERE username = $1 OR LOWER(email) = LOWER($2)" in normalized_query:
            username = str(args[0]).lower()
            email = str(args[1]).lower()
            for user in self.users.values():
                if user["username"] == username or user["email"] == email:
                    return {
                        "username": user["username"],
                        "email": user["email"],
                    }
            return None

        if "INSERT INTO app_users" in normalized_query:
            username = str(args[0]).lower()
            email = str(args[1]).lower()
            full_name = str(args[2]) if args[2] is not None else None
            hashed_password = str(args[3])
            self.users[username] = {
                "username": username,
                "email": email,
                "full_name": full_name,
                "hashed_password": hashed_password,
            }
            return {
                "username": username,
                "email": email,
                "full_name": full_name,
            }

        raise AssertionError(f"Unexpected query: {normalized_query}")

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_login_for_access_token():
    response = client.post("/token", data={"username": "admin", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert response.json()["username"] == "admin"

def test_login_failure():
    response = client.post("/token", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_register_user_returns_token_and_logs_them_in():
    fake_connection = FakeUserPgConnection()

    async def _override_postgres_connection() -> Any:
        yield fake_connection

    app.dependency_overrides[get_postgres_connection] = _override_postgres_connection

    try:
        response = client.post(
            "/register",
            json={
                "username": "Scientist.One",
                "email": "Scientist.One@BioNexus.dev",
                "password": "strongpassword",
                "full_name": "Scientist One",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["username"] == "scientist.one"
        assert body["token_type"] == "bearer"
        assert "access_token" in body

        login_response = client.post(
            "/token",
            data={"username": "scientist.one", "password": "strongpassword"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["username"] == "scientist.one"
    finally:
        app.dependency_overrides.pop(get_postgres_connection, None)


def test_register_user_rejects_duplicates():
    fake_connection = FakeUserPgConnection()
    fake_connection.users["scientist.one"] = {
        "username": "scientist.one",
        "email": "scientist.one@bionexus.dev",
        "full_name": "Scientist One",
        "hashed_password": get_password_hash("strongpassword"),
    }

    async def _override_postgres_connection() -> Any:
        yield fake_connection

    app.dependency_overrides[get_postgres_connection] = _override_postgres_connection

    try:
        response = client.post(
            "/register",
            json={
                "username": "scientist.one",
                "email": "fresh@bionexus.dev",
                "password": "strongpassword",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Username already exists"
    finally:
        app.dependency_overrides.pop(get_postgres_connection, None)


def test_login_for_registered_user_rejects_wrong_password():
    fake_connection = FakeUserPgConnection()
    fake_connection.users["scientist.one"] = {
        "username": "scientist.one",
        "email": "scientist.one@bionexus.dev",
        "full_name": "Scientist One",
        "hashed_password": get_password_hash("strongpassword"),
    }

    async def _override_postgres_connection() -> Any:
        yield fake_connection

    app.dependency_overrides[get_postgres_connection] = _override_postgres_connection

    try:
        response = client.post(
            "/token",
            data={"username": "scientist.one", "password": "incorrect-password"},
        )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_postgres_connection, None)

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


def test_get_disease_trends_authorized():
    class FakePgConnection:
        async def fetchrow(self, _query: str, disease_id: str, disease_name: str) -> dict[str, object] | None:
            assert disease_id == "alzheimers-disease"
            assert disease_name == "alzheimers-disease"
            return {
                "disease_id": "alzheimers-disease",
                "disease_name": "Alzheimer's disease",
                "clinical_summary": "summary",
                "frequency_timeline": [{"year": 2020, "study_count": 3}],
                "gene_distribution": [{"uniprot_id": "P11111", "gene_symbol": "APP", "association_score": 0.91}],
                "organ_affinity": [{"organ": "Brain", "value": 4}],
                "therapeutic_landscape": [
                    {
                        "chembl_id": "CHEMBL100",
                        "molecule_name": "Compound 100",
                        "uniprot_id": "P11111",
                        "gene_symbol": "APP",
                        "bioactivity_status": "Active",
                    }
                ],
                "updated_at": "2026-03-22T12:00:00Z",
            }

    async def _override_postgres_connection() -> Any:
        yield FakePgConnection()

    app.dependency_overrides[get_postgres_connection] = _override_postgres_connection
    token = client.post("/token", data={"username": "admin", "password": "password"}).json()["access_token"]

    try:
        response = client.get(
            "/api/v1/analytics/trends/alzheimers-disease",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["frequency_timeline"][0]["study_count"] == 3
        assert body["gene_distribution"][0]["uniprot_id"] == "P11111"
    finally:
        app.dependency_overrides.pop(get_postgres_connection, None)


def test_export_analytics_chart_authorized():
    token = client.post("/token", data={"username": "admin", "password": "password"}).json()["access_token"]

    response = client.post(
        "/api/v1/analytics/export",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "chart_type": "bar",
            "title": "Gene Frequency",
            "datasets": [{"gene_symbol": "APP", "association_score": 0.91}],
            "clinical_summary": "summary",
            "disease_name": "Alzheimer's disease",
            "x_key": "gene_symbol",
            "y_key": "association_score",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "bionexus-alzheimer-s-disease.html"
    assert "<!DOCTYPE html>" in body["html"]
    assert "Gene Frequency" in body["html"]
