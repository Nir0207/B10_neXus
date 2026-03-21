from unittest.mock import MagicMock, patch

from db_check import audit_and_fix_neo4j_schema, check_gene_disease_medicine_integrity


@patch("db_check.get_neo4j_driver")
def test_gene_disease_medicine_triad_integrity_success(
    mock_get_neo4j_driver: MagicMock,
) -> None:
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [
        {
            "gene_uniprot_id": "P00533",
            "disease_mesh_id": "D009369",
            "disease_name": "Neoplasms",
            "medicine_chembl_id": "CHEMBL1201587",
        },
        {
            "gene_uniprot_id": "Q9Y243",
            "disease_mesh_id": "D001943",
            "disease_name": "Breast Neoplasms",
            "medicine_chembl_id": "CHEMBL25",
        },
    ]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    is_valid, issues = check_gene_disease_medicine_integrity(limit=100)

    assert is_valid is True
    assert issues == []
    assert mock_session.run.call_count == 1
    query_text = mock_session.run.call_args.args[0]
    assert "MATCH (g:Gene)-[:ASSOCIATED_WITH]->(d:Disease)<-[:TREATS]-(m:Medicine)" in query_text


@patch("db_check.get_neo4j_driver")
def test_gene_disease_medicine_triad_integrity_detects_missing_fields(
    mock_get_neo4j_driver: MagicMock,
) -> None:
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [
        {
            "gene_uniprot_id": "P00533",
            "disease_mesh_id": "D009369",
            "disease_name": "",
            "medicine_chembl_id": "CHEMBL1201587",
        }
    ]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    is_valid, issues = check_gene_disease_medicine_integrity(limit=10)

    assert is_valid is False
    assert any("missing disease_name" in issue for issue in issues)


@patch("db_check.get_neo4j_driver")
def test_gene_disease_medicine_triad_integrity_detects_duplicate_paths(
    mock_get_neo4j_driver: MagicMock,
) -> None:
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [
        {
            "gene_uniprot_id": "P00533",
            "disease_mesh_id": "D009369",
            "disease_name": "Neoplasms",
            "medicine_chembl_id": "CHEMBL1201587",
        },
        {
            "gene_uniprot_id": "P00533",
            "disease_mesh_id": "D009369",
            "disease_name": "Neoplasms",
            "medicine_chembl_id": "CHEMBL1201587",
        },
    ]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    is_valid, issues = check_gene_disease_medicine_integrity(limit=10)

    assert is_valid is False
    assert any("duplicate triad path detected" in issue for issue in issues)


@patch("db_check.get_neo4j_driver")
def test_audit_and_fix_neo4j_schema_reports_missing_when_autofix_disabled(
    mock_get_neo4j_driver: MagicMock,
) -> None:
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.side_effect = [
        [{"name": "gene_uniprot_id"}],
        [{"name": "some_other_index"}],
    ]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    is_valid, issues, applied_fixes = audit_and_fix_neo4j_schema(auto_fix=False)

    assert is_valid is False
    assert applied_fixes == []
    assert any("disease_mesh_id" in issue for issue in issues)
    assert any("medicine_chembl_id" in issue for issue in issues)
    assert any("disease_name_fulltext" in issue for issue in issues)


@patch("db_check.get_neo4j_driver")
def test_audit_and_fix_neo4j_schema_creates_missing_artifacts_when_autofix_enabled(
    mock_get_neo4j_driver: MagicMock,
) -> None:
    issued_queries: list[str] = []
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session

    def run_side_effect(query: str, *args: object, **kwargs: object) -> list[dict[str, str]]:
        del args
        del kwargs
        issued_queries.append(query.strip())
        if query.startswith("SHOW CONSTRAINTS"):
            return []
        if query.startswith("SHOW INDEXES"):
            return []
        return []

    mock_session.run.side_effect = run_side_effect
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    is_valid, issues, applied_fixes = audit_and_fix_neo4j_schema(auto_fix=True)

    assert is_valid is True
    assert issues == []
    assert set(applied_fixes) == {
        "gene_uniprot_id",
        "disease_mesh_id",
        "medicine_chembl_id",
        "disease_name_fulltext",
    }
    assert any("CREATE CONSTRAINT gene_uniprot_id" in query for query in issued_queries)
    assert any("CREATE CONSTRAINT disease_mesh_id" in query for query in issued_queries)
    assert any("CREATE CONSTRAINT medicine_chembl_id" in query for query in issued_queries)
    assert any("CREATE FULLTEXT INDEX disease_name_fulltext" in query for query in issued_queries)
