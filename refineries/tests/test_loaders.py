"""
Tests for load_postgres.py and load_neo4j.py

All database connections are mocked — no real Postgres or Neo4j instance
is required.  These tests verify:
  - Correct SQL DML is dispatched (executemany called with right data)
  - Return values match the number of rows processed
  - Empty DataFrames are handled gracefully
  - Neo4j transactional writes are dispatched with expected batch payloads
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl


# ── CSV fixture factory ───────────────────────────────────────────────────────

def _write_csvs(tmp: Path) -> dict[str, Path]:
    proteins = tmp / "silver_proteins.csv"
    gene_map = tmp / "silver_gene_symbol_map.csv"
    reactome = tmp / "silver_reactome_map.csv"

    pl.DataFrame(
        {
            "uniprot_id": ["P38398", "P00533"],
            "hgnc_symbol": ["BRCA1", "EGFR"],
            "protein_name": [
                "Breast cancer type 1 susceptibility protein",
                "Epidermal growth factor receptor",
            ],
            "organism": ["Homo sapiens", "Homo sapiens"],
            "sequence": ["MDLSALRVEEV", "MRPSG"],
            "molecular_weight": [207721, 134277],
            "uniprot_kb_id": ["BRCA1_HUMAN", "EGFR_HUMAN"],
            "gene_synonyms": ["RNF53", ""],
            "annotation_score": [5.0, 5.0],
            "sequence_length": [1863, 1210],
            "data_source": ["UniProt", "UniProt"],
        }
    ).write_csv(proteins)

    pl.DataFrame(
        {
            "hgnc_symbol": ["BRCA1", "EGFR"],
            "uniprot_id": ["P38398", "P00533"],
            "source_file": ["BRCA1.json", "EGFR.json"],
        }
    ).write_csv(gene_map)

    pl.DataFrame(
        {
            "uniprot_id": ["P38398", "P38398"],
            "reactome_id": ["R-HSA-1221632", "R-HSA-3108214"],
            "pathway_name": ["Meiotic synapsis", "SUMOylation of DNA damage response"],
        }
    ).write_csv(reactome)

    return {"proteins": proteins, "gene_map": gene_map, "reactome": reactome}


def _mock_pg_conn() -> tuple[MagicMock, MagicMock]:
    """Return (mock_conn, mock_cursor) with context-manager wiring."""
    mock_cur = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cur


def _mock_neo4j_driver() -> tuple[MagicMock, MagicMock]:
    """Return (mock_driver, mock_session) with context-manager wiring."""
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return mock_driver, mock_session


# ── Postgres: load_proteins ───────────────────────────────────────────────────

class TestLoadProteins:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.csvs = _write_csvs(self.tmp)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp)

    def test_executemany_called_once(self) -> None:
        from load_postgres import load_proteins

        mock_conn, mock_cur = _mock_pg_conn()
        load_proteins(mock_conn, self.csvs["proteins"])
        mock_cur.executemany.assert_called_once()

    def test_returns_correct_row_count(self) -> None:
        from load_postgres import load_proteins

        mock_conn, mock_cur = _mock_pg_conn()
        result = load_proteins(mock_conn, self.csvs["proteins"])
        assert result == 2

    def test_row_dicts_contain_uniprot_id(self) -> None:
        from load_postgres import load_proteins

        mock_conn, mock_cur = _mock_pg_conn()
        load_proteins(mock_conn, self.csvs["proteins"])
        _, rows = mock_cur.executemany.call_args[0]
        assert all("uniprot_id" in r for r in rows)


# ── Postgres: load_genes ──────────────────────────────────────────────────────

class TestLoadGenes:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.csvs = _write_csvs(self.tmp)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp)

    def test_executemany_called_once(self) -> None:
        from load_postgres import load_genes

        mock_conn, mock_cur = _mock_pg_conn()
        load_genes(mock_conn, self.csvs["gene_map"], self.csvs["proteins"])
        mock_cur.executemany.assert_called_once()

    def test_returns_unique_gene_count(self) -> None:
        from load_postgres import load_genes

        mock_conn, mock_cur = _mock_pg_conn()
        result = load_genes(mock_conn, self.csvs["gene_map"], self.csvs["proteins"])
        assert result == 2


# ── Postgres: load_pathways ───────────────────────────────────────────────────

class TestLoadPathways:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.csvs = _write_csvs(self.tmp)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp)

    def test_executemany_called_for_pathways_and_links(self) -> None:
        from load_postgres import load_pathways

        mock_conn, mock_cur = _mock_pg_conn()
        load_pathways(mock_conn, self.csvs["reactome"])
        # Expect: executemany for pathway rows + executemany for pp rows = 2 calls
        assert mock_cur.executemany.call_count == 2

    def test_execute_called_for_ddl(self) -> None:
        from load_postgres import load_pathways

        mock_conn, mock_cur = _mock_pg_conn()
        load_pathways(mock_conn, self.csvs["reactome"])
        assert mock_cur.execute.call_count == 14

    def test_returns_pathway_plus_link_count(self) -> None:
        from load_postgres import load_pathways

        mock_conn, mock_cur = _mock_pg_conn()
        result = load_pathways(mock_conn, self.csvs["reactome"])
        # 2 unique pathways + 2 protein-pathway links = 4
        assert result == 4

    def test_empty_csv_returns_zero_without_db_calls(self) -> None:
        from load_postgres import load_pathways

        empty_csv = self.tmp / "empty_reactome.csv"
        pl.DataFrame(
            {"uniprot_id": [], "reactome_id": [], "pathway_name": []},
            schema={"uniprot_id": pl.Utf8, "reactome_id": pl.Utf8, "pathway_name": pl.Utf8},
        ).write_csv(empty_csv)

        mock_conn, mock_cur = _mock_pg_conn()
        result = load_pathways(mock_conn, empty_csv)
        assert result == 0
        mock_cur.executemany.assert_not_called()


# ── Neo4j: _load_genes_and_proteins ──────────────────────────────────────────

class TestNeo4jLoadGenesAndProteins:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.csvs = _write_csvs(self.tmp)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp)

    def test_execute_write_called_for_all_batches(self) -> None:
        from load_neo4j import (
            _ensure_constraints_tx,
            _load_genes_and_proteins,
            _merge_genes_tx,
        )

        driver, session = _mock_neo4j_driver()
        _load_genes_and_proteins(driver, self.csvs["proteins"], self.csvs["gene_map"])
        callbacks = [c.args[0] for c in session.execute_write.call_args_list]
        assert callbacks == [
            _ensure_constraints_tx,
            _merge_genes_tx,
        ]

    def test_gene_batch_contains_all_rows(self) -> None:
        from load_neo4j import _load_genes_and_proteins, _merge_genes_tx

        driver, session = _mock_neo4j_driver()
        _load_genes_and_proteins(driver, self.csvs["proteins"], self.csvs["gene_map"])
        gene_call = next(
            c for c in session.execute_write.call_args_list if c.args[0] == _merge_genes_tx
        )
        rows = gene_call.args[1]
        assert len(rows) == 2
        assert {row["uniprot_id"] for row in rows} == {"P38398", "P00533"}
        assert {row["hgnc_symbol"] for row in rows} == {"BRCA1", "EGFR"}

    def test_gene_batch_contains_unique_symbols(self) -> None:
        from load_neo4j import _load_genes_and_proteins, _merge_genes_tx

        driver, session = _mock_neo4j_driver()
        _load_genes_and_proteins(driver, self.csvs["proteins"], self.csvs["gene_map"])
        gene_call = next(
            c for c in session.execute_write.call_args_list if c.args[0] == _merge_genes_tx
        )
        rows = gene_call.args[1]
        assert len(rows) == 2
        assert {row["hgnc_symbol"] for row in rows} == {"BRCA1", "EGFR"}


# ── Neo4j: _load_pathways ─────────────────────────────────────────────────────

class TestNeo4jLoadPathways:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.csvs = _write_csvs(self.tmp)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp)

    def test_execute_write_called_for_constraints_and_pathway_batches(self) -> None:
        from load_neo4j import (
            _ensure_constraints_tx,
            _load_pathways,
            _merge_involved_in_tx,
            _merge_pathways_tx,
        )

        driver, session = _mock_neo4j_driver()
        _load_pathways(driver, self.csvs["reactome"])
        callbacks = [c.args[0] for c in session.execute_write.call_args_list]
        assert callbacks == [
            _ensure_constraints_tx,
            _merge_pathways_tx,
            _merge_involved_in_tx,
        ]

    def test_pathway_batch_contains_unique_rows(self) -> None:
        from load_neo4j import _load_pathways, _merge_pathways_tx

        driver, session = _mock_neo4j_driver()
        _load_pathways(driver, self.csvs["reactome"])
        pathway_call = next(
            c for c in session.execute_write.call_args_list if c.args[0] == _merge_pathways_tx
        )
        rows = pathway_call.args[1]
        assert len(rows) == 2
        assert {row["reactome_id"] for row in rows} == {"R-HSA-1221632", "R-HSA-3108214"}

    def test_empty_csv_skips_all_session_calls(self) -> None:
        from load_neo4j import _load_pathways

        empty_csv = self.tmp / "empty_reactome.csv"
        pl.DataFrame(
            {"uniprot_id": [], "reactome_id": [], "pathway_name": []},
            schema={"uniprot_id": pl.Utf8, "reactome_id": pl.Utf8, "pathway_name": pl.Utf8},
        ).write_csv(empty_csv)

        driver, session = _mock_neo4j_driver()
        _load_pathways(driver, empty_csv)
        session.execute_write.assert_not_called()
