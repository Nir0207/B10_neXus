from __future__ import annotations

import csv
import json
from pathlib import Path

from bionexus_intelligence.repositories import JsonOpenTargetsRepository, PostgresStudyRepository, _safe_int


def test_json_open_targets_repo_filters_by_gene(tmp_path: Path) -> None:
    payload = {
        "data": {
            "disease": {
                "name": "Liver disease",
                "associatedTargets": {
                    "rows": [
                        {
                            "score": 0.9,
                            "target": {"approvedSymbol": "EGFR"},
                        },
                        {
                            "score": 0.2,
                            "target": {"approvedSymbol": "BRCA1"},
                        },
                    ]
                },
            }
        }
    }
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    repo = JsonOpenTargetsRepository(evidence_path)
    rows = repo.find_evidence_for_gene("egfr", limit=5)

    assert len(rows) == 1
    assert rows[0].target_symbol == "EGFR"
    assert rows[0].disease_name == "Liver disease"
    assert rows[0].evidence_score == 0.9


def test_json_open_targets_repo_handles_null_disease(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text('{"data": {"disease": null}}', encoding="utf-8")

    repo = JsonOpenTargetsRepository(evidence_path)
    assert repo.find_evidence_for_gene("EGFR", limit=5) == []


def test_seed_rows_deidentify_study_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "silver_ncbi_studies.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "uid",
                "accession",
                "title",
                "summary",
                "publication_date",
                "sample_count",
                "platform",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "uid": "123",
                "accession": "GSE123",
                "title": "Study title",
                "summary": "Email test@hospital.org call 123-456-7890 Patient ID: ABC12345",
                "publication_date": "2026/03/21",
                "sample_count": "10",
                "platform": "15433",
            }
        )

    repo = PostgresStudyRepository("postgresql://unused")
    rows = list(repo._iter_seed_rows(csv_path))

    assert len(rows) == 1
    summary = rows[0]["deidentified_summary"]
    assert "test@hospital.org" not in summary
    assert "123-456-7890" not in summary
    assert "ABC12345" not in summary
    assert "[REDACTED_EMAIL]" in summary
    assert "[REDACTED_PHONE]" in summary
    assert "[REDACTED_PATIENT_ID]" in summary


def test_safe_int_parsing() -> None:
    assert _safe_int("42") == 42
    assert _safe_int(" ") is None
    assert _safe_int("abc") is None
    assert _safe_int(None) is None
