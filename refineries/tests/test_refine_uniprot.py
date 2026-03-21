"""
Tests for refine_uniprot.py

Covers:
- Field extraction from a single UniProt entry (_extract_record)
- Reactome mapping extraction (_extract_reactome_mappings)
- Full pipeline: file reading → DataFrames → CSV artefacts
- No-data-loss invariant across multiple input files
- Idempotency: files not re-processed after mark_processed
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from stubs import BRCA1_RECORD, BRCA1_STUB, EGFR_RECORD, EGFR_STUB
from refine_uniprot import (
    _extract_reactome_mappings,
    _extract_record,
    refine_uniprot,
)


# ── _extract_record ───────────────────────────────────────────────────────────

class TestExtractRecord:
    def test_primary_accession_becomes_uniprot_id(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["uniprot_id"] == "P38398"

    def test_gene_name_extracted_as_hgnc_symbol(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["hgnc_symbol"] == "BRCA1"

    def test_gene_synonyms_pipe_joined(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["gene_synonyms"] == "RNF53"

    def test_protein_name_extracted(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert "Breast cancer" in rec["protein_name"]

    def test_organism_extracted(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["organism"] == "Homo sapiens"

    def test_sequence_length_and_weight(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["sequence_length"] == 1863
        assert rec["molecular_weight"] == 207721

    def test_sequence_value_present(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["sequence"].startswith("MDLSALR")

    def test_missing_genes_returns_empty_string(self) -> None:
        entry = {**BRCA1_RECORD, "genes": []}
        rec = _extract_record(entry)
        assert rec["hgnc_symbol"] == ""
        assert rec["gene_synonyms"] == ""

    def test_no_synonyms_yields_empty_string(self) -> None:
        rec = _extract_record(EGFR_RECORD)
        assert rec["gene_synonyms"] == ""

    def test_annotation_score_preserved(self) -> None:
        rec = _extract_record(BRCA1_RECORD)
        assert rec["annotation_score"] == 5.0


# ── _extract_reactome_mappings ────────────────────────────────────────────────

class TestExtractReactomeMappings:
    def test_only_reactome_xrefs_returned(self) -> None:
        mappings = _extract_reactome_mappings("P38398", BRCA1_RECORD)
        assert all(m["reactome_id"].startswith("R-HSA-") for m in mappings)

    def test_correct_count_excludes_non_reactome(self) -> None:
        # BRCA1_RECORD has 2 Reactome + 1 STRING xref
        mappings = _extract_reactome_mappings("P38398", BRCA1_RECORD)
        assert len(mappings) == 2

    def test_uniprot_id_propagated_to_all_rows(self) -> None:
        mappings = _extract_reactome_mappings("P38398", BRCA1_RECORD)
        assert all(m["uniprot_id"] == "P38398" for m in mappings)

    def test_pathway_name_populated(self) -> None:
        mappings = _extract_reactome_mappings("P38398", BRCA1_RECORD)
        names = {m["pathway_name"] for m in mappings}
        assert "Meiotic synapsis" in names

    def test_pathway_id_populated(self) -> None:
        mappings = _extract_reactome_mappings("P38398", BRCA1_RECORD)
        ids = {m["reactome_id"] for m in mappings}
        assert "R-HSA-1221632" in ids

    def test_no_reactome_xrefs_returns_empty_list(self) -> None:
        entry = {**BRCA1_RECORD, "uniProtKBCrossReferences": []}
        assert _extract_reactome_mappings("P38398", entry) == []

    def test_egfr_has_no_reactome_mappings(self) -> None:
        assert _extract_reactome_mappings("P00533", EGFR_RECORD) == []


# ── refine_uniprot (integration) ─────────────────────────────────────────────

class TestRefineUniProt:
    def setup_method(self) -> None:
        self.raw_dir = Path(tempfile.mkdtemp())
        self.out_dir = Path(tempfile.mkdtemp())
        (self.raw_dir / "BRCA1.json").write_text(
            json.dumps(BRCA1_STUB), encoding="utf-8"
        )

    def teardown_method(self) -> None:
        shutil.rmtree(self.raw_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_returns_three_dataframes(self) -> None:
        result = refine_uniprot(self.raw_dir, self.out_dir, skip_processed=False)
        assert len(result) == 3
        for df in result:
            assert isinstance(df, pl.DataFrame)

    def test_no_data_loss_single_file(self) -> None:
        proteins_df, _, _ = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        assert len(proteins_df) == len(BRCA1_STUB["results"])

    def test_no_data_loss_two_files(self) -> None:
        (self.raw_dir / "EGFR.json").write_text(
            json.dumps(EGFR_STUB), encoding="utf-8"
        )
        proteins_df, _, _ = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        assert len(proteins_df) == 2
        assert set(proteins_df["uniprot_id"].to_list()) == {"P38398", "P00533"}

    def test_proteins_csv_written(self) -> None:
        refine_uniprot(self.raw_dir, self.out_dir, skip_processed=False)
        assert (self.out_dir / "silver_proteins.csv").exists()

    def test_gene_map_csv_written(self) -> None:
        refine_uniprot(self.raw_dir, self.out_dir, skip_processed=False)
        assert (self.out_dir / "silver_gene_symbol_map.csv").exists()

    def test_reactome_csv_written(self) -> None:
        refine_uniprot(self.raw_dir, self.out_dir, skip_processed=False)
        assert (self.out_dir / "silver_reactome_map.csv").exists()

    def test_proteins_df_has_required_columns(self) -> None:
        proteins_df, _, _ = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        required = {
            "uniprot_id",
            "hgnc_symbol",
            "protein_name",
            "organism",
            "molecular_weight",
            "sequence_length",
        }
        assert required.issubset(set(proteins_df.columns))

    def test_uniprot_id_is_unique_primary_key(self) -> None:
        proteins_df, _, _ = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        assert proteins_df["uniprot_id"].n_unique() == len(proteins_df)

    def test_reactome_rows_match_xref_count(self) -> None:
        _, _, reactome_df = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        # BRCA1 has 2 Reactome xrefs
        assert len(reactome_df) == 2

    def test_gene_map_uses_hgnc_symbol_column(self) -> None:
        _, gene_map_df, _ = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        assert {"uniprot_id", "hgnc_symbol", "source_file"}.issubset(set(gene_map_df.columns))

    def test_egfr_no_reactome_yields_empty_df(self) -> None:
        (self.raw_dir / "EGFR.json").write_text(
            json.dumps(EGFR_STUB), encoding="utf-8"
        )
        # Replace BRCA1 with EGFR only
        (self.raw_dir / "BRCA1.json").unlink()
        _, _, reactome_df = refine_uniprot(
            self.raw_dir, self.out_dir, skip_processed=False
        )
        assert reactome_df.is_empty()

    def test_raises_on_empty_directory(self) -> None:
        empty = Path(tempfile.mkdtemp())
        try:
            with pytest.raises(FileNotFoundError):
                refine_uniprot(empty, self.out_dir, skip_processed=False)
        finally:
            shutil.rmtree(empty)

    def test_idempotency_skips_processed_files(self) -> None:
        import idempotency

        manifest = self.out_dir / ".test_manifest.json"
        with patch.object(idempotency, "MANIFEST_PATH", manifest):
            # First run — processes the file
            refine_uniprot(self.raw_dir, self.out_dir, skip_processed=True)
            # Second run — CSVs loaded from disk, manifest unchanged
            proteins_df, _, _ = refine_uniprot(
                self.raw_dir, self.out_dir, skip_processed=True
            )
            assert len(proteins_df) == 1

    def test_incremental_change_rebuilds_full_snapshot(self) -> None:
        import idempotency

        (self.raw_dir / "EGFR.json").write_text(
            json.dumps(EGFR_STUB), encoding="utf-8"
        )
        manifest = self.out_dir / ".test_manifest.json"

        with patch.object(idempotency, "MANIFEST_PATH", manifest):
            proteins_df, _, _ = refine_uniprot(
                self.raw_dir, self.out_dir, skip_processed=True
            )
            assert len(proteins_df) == 2

            updated_egfr = json.loads(json.dumps(EGFR_STUB))
            updated_egfr["results"][0]["proteinDescription"]["recommendedName"][
                "fullName"
            ]["value"] = "Epidermal growth factor receptor v2"
            (self.raw_dir / "EGFR.json").write_text(
                json.dumps(updated_egfr), encoding="utf-8"
            )

            proteins_df, _, _ = refine_uniprot(
                self.raw_dir, self.out_dir, skip_processed=True
            )
            assert len(proteins_df) == 2
            assert set(proteins_df["uniprot_id"].to_list()) == {"P38398", "P00533"}
            assert proteins_df.filter(pl.col("uniprot_id") == "P00533").item(
                0, "protein_name"
            ) == "Epidermal growth factor receptor v2"

    def test_manifest_not_updated_when_refine_fails(self) -> None:
        import idempotency

        (self.raw_dir / "BROKEN.json").write_text("{not-valid-json", encoding="utf-8")
        manifest = self.out_dir / ".test_manifest.json"
        with patch.object(idempotency, "MANIFEST_PATH", manifest):
            with pytest.raises(json.JSONDecodeError):
                refine_uniprot(self.raw_dir, self.out_dir, skip_processed=True)
            assert not manifest.exists()
