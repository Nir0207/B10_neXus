import pytest
from unittest.mock import MagicMock, patch
from db_check import check_uniprot_consistency


@patch("db_check.get_postgres_connection")
@patch("db_check.get_neo4j_driver")
def test_check_uniprot_consistency_success(mock_get_neo4j_driver, mock_get_postgres_connection):
    # Mock PostgreSQL
    mock_pg_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_pg_conn.cursor.return_value.__enter__.return_value = mock_cursor
    # Postgres returns 3 mapping entries
    mock_cursor.fetchall.return_value = [("P12345",), ("Q67890",), ("O11111",)]
    mock_get_postgres_connection.return_value = mock_pg_conn

    # Mock Neo4j
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    # Neo4j returns the same 3 mapping entries
    mock_session.run.return_value = [{"uniprot_id": "P12345"}, {"uniprot_id": "Q67890"}, {"uniprot_id": "O11111"}]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    consistent, missing = check_uniprot_consistency()
    
    assert consistent is True
    assert len(missing) == 0


@patch("db_check.get_postgres_connection")
@patch("db_check.get_neo4j_driver")
def test_check_uniprot_consistency_failure(mock_get_neo4j_driver, mock_get_postgres_connection):
    # Mock PostgreSQL
    mock_pg_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_pg_conn.cursor.return_value.__enter__.return_value = mock_cursor
    # Postgres returns 3 mapping entries
    mock_cursor.fetchall.return_value = [("P12345",), ("Q67890",), ("O11111",)]
    mock_get_postgres_connection.return_value = mock_pg_conn

    # Mock Neo4j
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
    # Neo4j is missing "O11111"
    mock_session.run.return_value = [{"uniprot_id": "P12345"}, {"uniprot_id": "Q67890"}]
    mock_get_neo4j_driver.return_value = mock_neo4j_driver

    consistent, missing = check_uniprot_consistency()
    
    assert consistent is False
    assert "O11111" in missing
    assert len(missing) == 1


@patch("db_check.get_postgres_connection")
def test_check_uniprot_consistency_connection_error(mock_get_postgres_connection):
    # Mock Postgres connection to fail
    mock_get_postgres_connection.side_effect = Exception("Connection refused")
    
    consistent, _ = check_uniprot_consistency()
    
    assert consistent is False
