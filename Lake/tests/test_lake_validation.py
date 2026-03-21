from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path
from unittest.mock import patch

LAKE_ROOT = Path(__file__).resolve().parents[1]


def lake_file(path: str) -> Path:
    return LAKE_ROOT / path


def read(path: str) -> str:
    return lake_file(path).read_text(encoding="utf-8")


class _FakeDuckDBConnection:
    def __init__(self):
        self.queries: list[str] = []

    def execute(self, query: str):
        self.queries.append(query)
        return self

    def fetchall(self):
        return []

    def close(self):
        return None


def _load_module(module_name: str, path: Path, injected_modules: dict[str, object] | None = None):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    if injected_modules:
        with patch.dict(sys.modules, injected_modules, clear=False):
            spec.loader.exec_module(module)
    else:
        spec.loader.exec_module(module)
    return module


def test_expected_lake_files_exist():
    expected = {
        "docker-compose.yml",
        "Makefile",
        "requirements.txt",
        "scripts/duckdb_lake_init.py",
        "scripts/health_check.py",
        "init-scripts/postgres-init.sql",
        "init-scripts/neo4j-init.cypher",
        "init-scripts/mongodb-init.js",
    }
    missing = [path for path in sorted(expected) if not lake_file(path).exists()]
    assert not missing, f"Missing Lake files: {missing}"


def test_docker_compose_core_services_and_healthchecks():
    compose = read("docker-compose.yml")
    for name in ("refinery", "postgres", "neo4j", "mongodb"):
        assert re.search(rf"^\s{{2}}{name}:\s*$", compose, flags=re.MULTILINE)

    healthchecks = re.findall(r"^\s{4}healthcheck:\s*$", compose, flags=re.MULTILINE)
    assert len(healthchecks) >= 3


def test_docker_compose_refinery_to_neo4j_data_plane():
    compose = read("docker-compose.yml")

    assert "NEO4J_URI: bolt://neo4j:7687" in compose
    assert "NEO4J_server_bolt_advertised__address: neo4j:7687" in compose
    assert "NEO4J_server_bolt_advertised__address: localhost:7687" not in compose
    assert "bionexus-data-plane:" in compose
    assert re.search(r"^\s{2}bionexus-data-plane:\s*$", compose, flags=re.MULTILINE)
    assert re.search(r"^\s{4}internal:\s*true\s*$", compose, flags=re.MULTILINE)
    assert "subnet: 10.250.0.0/24" in compose
    assert "subnet: 10.250.1.0/24" in compose


def test_makefile_has_core_targets():
    makefile_text = read("Makefile")
    targets = {
        match.group(1)
        for match in re.finditer(r"^([a-zA-Z0-9_.-]+):", makefile_text, flags=re.MULTILINE)
    }

    expected_targets = {
        "up",
        "down",
        "restart",
        "health",
        "test",
        "deps",
        "lake-init",
        "db-init",
        "init",
        "clean",
    }
    assert expected_targets.issubset(targets)


def test_requirements_pin_versions_for_core_deps():
    requirements = [
        line.strip()
        for line in read("requirements.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert requirements
    assert all("==" in requirement for requirement in requirements)

    requirement_names = {line.split("==", 1)[0] for line in requirements}
    for pkg in ("duckdb", "polars", "pandas", "pydantic", "requests"):
        assert pkg in requirement_names


def test_postgres_init_uses_postgres_compatible_index_syntax():
    sql = read("init-scripts/postgres-init.sql")

    # MySQL-style inline INDEX inside CREATE TABLE is invalid in Postgres.
    table_blocks = re.findall(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS[\s\S]*?\);",
        sql,
        flags=re.IGNORECASE,
    )
    assert table_blocks
    assert all(not re.search(r"\bINDEX\s+\w+\s*\(", block, flags=re.IGNORECASE) for block in table_blocks)

    for stmt in (
        "CREATE INDEX IF NOT EXISTS idx_uniprot_acc ON silver.proteins (uniprot_accession);",
        "CREATE INDEX IF NOT EXISTS idx_gene_name ON silver.proteins (gene_name);",
        "CREATE INDEX IF NOT EXISTS idx_hgnc ON silver.genes (hgnc_symbol);",
        "CREATE INDEX IF NOT EXISTS idx_ensembl ON silver.genes (ensembl_id);",
        "CREATE INDEX IF NOT EXISTS idx_mondo ON silver.diseases (mondo_id);",
        "CREATE INDEX IF NOT EXISTS idx_disease_name ON silver.diseases (disease_name);",
        "CREATE INDEX IF NOT EXISTS idx_chembl ON silver.compounds (chembl_id);",
    ):
        assert stmt in sql


def test_neo4j_init_uses_neo4j_5_constraint_syntax():
    cypher = read("init-scripts/neo4j-init.cypher")

    assert "ASSERT" not in cypher
    assert "REQUIRE g.hgnc_symbol IS UNIQUE" in cypher
    assert "REQUIRE p.uniprot_accession IS UNIQUE" in cypher
    assert "REQUIRE d.mondo_id IS UNIQUE" in cypher
    assert "REQUIRE c.chembl_id IS UNIQUE" in cypher


def test_mongodb_init_is_idempotent_for_collections_and_user():
    script = read("init-scripts/mongodb-init.js")

    assert "function ensureCollection" in script
    assert "database.getCollectionNames()" in script
    assert "database.getUser('bionexus_user')" in script
    assert "database.updateUser('bionexus_user', { roles });" in script


def test_health_check_resolves_lake_workspace_and_has_docker_check():
    module = _load_module(
        "health_check_under_test",
        lake_file("scripts/health_check.py"),
    )

    checker = module.BioNexusHealthCheck()
    assert checker.workspace == LAKE_ROOT
    assert hasattr(checker, "check_docker")
    assert callable(checker.check_docker)


def test_health_check_run_all_calls_expected_checks_in_order(monkeypatch):
    module = _load_module(
        "health_check_under_test_order",
        lake_file("scripts/health_check.py"),
    )

    checker = module.BioNexusHealthCheck()
    calls: list[str] = []

    monkeypatch.setattr(checker, "check_files", lambda: calls.append("check_files"))
    monkeypatch.setattr(checker, "check_docker", lambda: calls.append("check_docker"))
    monkeypatch.setattr(checker, "check_services", lambda: calls.append("check_services"))
    monkeypatch.setattr(checker, "check_databases", lambda: calls.append("check_databases"))
    monkeypatch.setattr(checker, "check_duckdb", lambda: calls.append("check_duckdb"))
    monkeypatch.setattr(checker, "check_python", lambda: calls.append("check_python"))
    monkeypatch.setattr(checker, "summary", lambda: 0)

    assert checker.run_all() == 0
    assert calls == [
        "check_files",
        "check_docker",
        "check_services",
        "check_databases",
        "check_duckdb",
        "check_python",
    ]


def test_duckdb_init_uses_supported_types_and_schema_summary_query():
    script = read("scripts/duckdb_lake_init.py")

    assert "raw_xml VARCHAR" in script
    assert "raw_xml XML" not in script
    assert "SELECT table_schema AS schema_name" in script
    assert "GROUP BY table_schema;" in script


def test_duckdb_init_creates_sequences_before_nextval_usage(tmp_path):
    fake_conn = _FakeDuckDBConnection()
    fake_duckdb = types.SimpleNamespace(connect=lambda _: fake_conn)
    module = _load_module(
        "duckdb_lake_init_under_test",
        lake_file("scripts/duckdb_lake_init.py"),
        injected_modules={"duckdb": fake_duckdb},
    )

    initializer = module.DuckDBLakeInitializer(str(tmp_path / "bionexus.duckdb"))
    initializer.create_bronze_schema()
    initializer.create_parquet_registry()

    all_queries = "\n".join(fake_conn.queries)

    audit_seq_pos = all_queries.find("CREATE SEQUENCE IF NOT EXISTS audit_seq")
    audit_table_pos = all_queries.find("DEFAULT nextval('audit_seq')")
    parquet_seq_pos = all_queries.find("CREATE SEQUENCE IF NOT EXISTS parquet_seq")
    parquet_table_pos = all_queries.find("DEFAULT nextval('parquet_seq')")

    assert audit_seq_pos != -1 and audit_table_pos != -1 and audit_seq_pos < audit_table_pos
    assert parquet_seq_pos != -1 and parquet_table_pos != -1 and parquet_seq_pos < parquet_table_pos
