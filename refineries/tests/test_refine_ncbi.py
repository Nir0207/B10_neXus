"""
Tests for refine_ncbi.py

Covers:
- Field extraction from a single NCBI esummary entry (_extract_study)
- Full pipeline: file reading → DataFrame → CSV artefact
- No-data-loss for all UIDs in the payload
- Edge cases: missing UIDs, zero samples
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from tests.stubs import NCBI_STUB
from refine_ncbi import _extract_study, refine_ncbi


# ── _extract_study ────────────────────────────────────────────────────────────

class TestExtractStudy:
    def test_uid_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["uid"] == "200267911"

    def test_accession_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["accession"] == "GSE267911"

    def test_title_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert "KAT2B" in rec["title"]

    def test_taxon_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["taxon"] == "Homo sapiens"

    def test_sample_count_one_sample(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["sample_count"] == 1

    def test_sample_count_zero_samples(self) -> None:
        rec = _extract_study("200307271", NCBI_STUB["result"]["200307271"])
        assert rec["sample_count"] == 0

    def test_publication_date_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["publication_date"] == "2026/03/18"

    def test_platform_preserved(self) -> None:
        rec = _extract_study("200267911", NCBI_STUB["result"]["200267911"])
        assert rec["platform"] == "15433"

    def test_missing_fields_default_to_empty_string(self) -> None:
        rec = _extract_study("999", {})
        assert rec["accession"] == ""
        assert rec["sample_count"] == 0


# ── refine_ncbi (integration) ─────────────────────────────────────────────────

class TestRefineNCBI:
    def setup_method(self) -> None:
        self.raw_dir = Path(tempfile.mkdtemp())
        self.out_dir = Path(tempfile.mkdtemp())
        (self.raw_dir / "BRCA1_studies.json").write_text(
            json.dumps(NCBI_STUB), encoding="utf-8"
        )

    def teardown_method(self) -> None:
        shutil.rmtree(self.raw_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_returns_polars_dataframe(self) -> None:
        df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        assert isinstance(df, pl.DataFrame)

    def test_no_data_loss_all_uids_present(self) -> None:
        df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        assert len(df) == len(NCBI_STUB["result"]["uids"])

    def test_correct_uids_in_output(self) -> None:
        df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        assert set(df["uid"].to_list()) == {"200267911", "200307271"}

    def test_csv_written(self) -> None:
        refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        assert (self.out_dir / "silver_ncbi_studies.csv").exists()

    def test_required_columns_present(self) -> None:
        df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        required = {"uid", "accession", "title", "taxon", "publication_date", "sample_count"}
        assert required.issubset(set(df.columns))

    def test_multiple_files_all_rows_present(self) -> None:
        second_stub = {
            "header": {"type": "esummary", "version": "0.3"},
            "result": {
                "uids": ["200999999"],
                "200999999": {
                    "uid": "200999999",
                    "accession": "GSE999999",
                    "title": "Extra Study",
                    "summary": "",
                    "gpl": "12345",
                    "taxon": "Homo sapiens",
                    "entrytype": "GSE",
                    "gdstype": "Other",
                    "pdat": "2026/01/01",
                    "samples": [],
                },
            },
        }
        (self.raw_dir / "EGFR_studies.json").write_text(
            json.dumps(second_stub), encoding="utf-8"
        )
        df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=False)
        assert len(df) == 3  # 2 from BRCA1_studies + 1 from EGFR_studies

    def test_uid_absent_from_result_dict_is_skipped(self) -> None:
        """UIDs listed in 'uids' but absent as keys must be silently skipped."""
        stub_with_ghost = {
            "header": {"type": "esummary", "version": "0.3"},
            "result": {
                "uids": ["111", "999"],  # 999 is not in result
                "111": {
                    "uid": "111",
                    "accession": "GSE111",
                    "title": "Real study",
                    "summary": "",
                    "gpl": "1",
                    "taxon": "Homo sapiens",
                    "entrytype": "GSE",
                    "gdstype": "Other",
                    "pdat": "2026/01/01",
                    "samples": [],
                },
            },
        }
        ghost_dir = Path(tempfile.mkdtemp())
        out = Path(tempfile.mkdtemp())
        try:
            (ghost_dir / "ghost.json").write_text(
                json.dumps(stub_with_ghost), encoding="utf-8"
            )
            df = refine_ncbi(ghost_dir, out, skip_processed=False)
            assert len(df) == 1
            assert df["accession"][0] == "GSE111"
        finally:
            shutil.rmtree(ghost_dir)
            shutil.rmtree(out)

    def test_raises_on_empty_directory(self) -> None:
        empty = Path(tempfile.mkdtemp())
        try:
            with pytest.raises(FileNotFoundError):
                refine_ncbi(empty, self.out_dir, skip_processed=False)
        finally:
            shutil.rmtree(empty)

    def test_incremental_change_rebuilds_full_snapshot(self) -> None:
        import idempotency

        second_stub = {
            "header": {"type": "esummary", "version": "0.3"},
            "result": {
                "uids": ["200999999"],
                "200999999": {
                    "uid": "200999999",
                    "accession": "GSE999999",
                    "title": "Extra Study",
                    "summary": "",
                    "gpl": "12345",
                    "taxon": "Homo sapiens",
                    "entrytype": "GSE",
                    "gdstype": "Other",
                    "pdat": "2026/01/01",
                    "samples": [],
                },
            },
        }
        (self.raw_dir / "EGFR_studies.json").write_text(
            json.dumps(second_stub), encoding="utf-8"
        )
        manifest = self.out_dir / ".test_manifest.json"
        with patch.object(idempotency, "MANIFEST_PATH", manifest):
            df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=True)
            assert len(df) == 3

            updated_stub = json.loads(json.dumps(second_stub))
            updated_stub["result"]["200999999"]["title"] = "Extra Study Updated"
            (self.raw_dir / "EGFR_studies.json").write_text(
                json.dumps(updated_stub), encoding="utf-8"
            )

            df = refine_ncbi(self.raw_dir, self.out_dir, skip_processed=True)
            assert len(df) == 3
            assert "GSE267911" in set(df["accession"].to_list())
            assert "GSE307271" in set(df["accession"].to_list())
            assert "GSE999999" in set(df["accession"].to_list())

    def test_manifest_not_updated_when_refine_fails(self) -> None:
        import idempotency

        (self.raw_dir / "BROKEN.json").write_text("{not-valid-json", encoding="utf-8")
        manifest = self.out_dir / ".test_manifest.json"
        with patch.object(idempotency, "MANIFEST_PATH", manifest):
            with pytest.raises(json.JSONDecodeError):
                refine_ncbi(self.raw_dir, self.out_dir, skip_processed=True)
            assert not manifest.exists()
