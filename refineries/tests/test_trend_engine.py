from __future__ import annotations

import json
from pathlib import Path

from psycopg.types.json import Jsonb

from trend_engine import build_disease_records, load_disease_intelligence


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_disease_records_prefers_open_targets_and_uses_uniprot_fallback(
    tmp_path: Path,
) -> None:
    silver_dir = tmp_path / "silver"
    raw_uniprot_dir = tmp_path / "raw" / "uniprot"
    raw_ot_dir = tmp_path / "raw" / "opentargets"
    studies_csv = silver_dir / "silver_ncbi_studies.csv"
    proteins_csv = silver_dir / "silver_proteins.csv"

    silver_dir.mkdir(parents=True)
    proteins_csv.write_text(
        "\n".join(
            [
                "uniprot_id,uniprot_kb_id,hgnc_symbol,gene_synonyms,protein_name,organism,sequence_length,molecular_weight,annotation_score,sequence,data_source",
                "P11111,FOO_HUMAN,FOO,,Foo protein,Homo sapiens,100,10000,5.0,MAAA,UniProt",
                "P22222,BAR_HUMAN,BAR,,Bar protein,Homo sapiens,120,12000,4.0,MBBB,UniProt",
            ]
        ),
        encoding="utf-8",
    )
    studies_csv.write_text(
        "\n".join(
            [
                "uid,accession,gene_symbol,title,summary,taxon,gds_type,entry_type,publication_date,sample_count,platform,source_file",
                '1,GSE1,FOO,"Alzheimer cohort","FOO signal",human,type,entry,2020/02/01,4,GPL1,foo.json',
                '2,GSE2,FOO,"Alzheimer follow-up","FOO validation",human,type,entry,2021/03/04,5,GPL1,foo.json',
                '3,GSE3,BAR,"Neural tissue panel","BAR profiling",human,type,entry,2021/08/09,6,GPL2,bar.json',
            ]
        ),
        encoding="utf-8",
    )

    _write_json(
        raw_uniprot_dir / "FOO.json",
        {
            "results": [
                {
                    "primaryAccession": "P11111",
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "FOO"}}],
                    "comments": [
                        {
                            "commentType": "DISEASE",
                            "disease": {
                                "diseaseId": "Fallback disease",
                                "evidences": [{"id": "1"}, {"id": "2"}],
                            },
                        },
                        {
                            "commentType": "TISSUE SPECIFICITY",
                            "texts": [{"value": "Widely expressed in brain tissue."}],
                        },
                    ],
                    "uniProtKBCrossReferences": [
                        {"database": "ChEMBL", "id": "CHEMBL100"},
                    ],
                }
            ]
        },
    )
    _write_json(
        raw_uniprot_dir / "BAR.json",
        {
            "results": [
                {
                    "primaryAccession": "P22222",
                    "organism": {"scientificName": "Homo sapiens"},
                    "genes": [{"geneName": {"value": "BAR"}}],
                    "comments": [
                        {
                            "commentType": "TISSUE SPECIFICITY",
                            "texts": [{"value": "Enriched in brain and neural tissue."}],
                        }
                    ],
                    "uniProtKBCrossReferences": [
                        {"database": "ChEMBL", "id": "CHEMBL200"},
                    ],
                }
            ]
        },
    )
    _write_json(
        raw_ot_dir / "alzheimers.json",
        {
            "data": {
                "disease": {
                    "id": "EFO_0000249",
                    "name": "Alzheimer's disease",
                    "associatedTargets": {
                        "rows": [
                            {
                                "score": 0.92,
                                "target": {
                                    "approvedSymbol": "FOO",
                                    "proteinIds": ["P11111"],
                                },
                            },
                            {
                                "score": 0.71,
                                "target": {
                                    "approvedSymbol": "BAR",
                                    "proteinIds": ["P22222"],
                                },
                            },
                        ]
                    },
                }
            }
        },
    )

    records = build_disease_records(
        raw_uniprot_dir=raw_uniprot_dir,
        raw_opentargets_dir=raw_ot_dir,
        studies_csv_path=studies_csv,
        proteins_csv_path=proteins_csv,
        conn=None,
    )

    assert len(records) == 2
    alzheimers = next(record for record in records if record["disease_name"] == "Alzheimer's disease")
    fallback = next(record for record in records if record["disease_name"] == "Fallback disease")

    assert alzheimers["gene_distribution"][0]["gene_symbol"] == "FOO"
    assert alzheimers["gene_distribution"][0]["association_source"] == "Open Targets"
    assert alzheimers["frequency_timeline"] == [
        {"year": 2020, "study_count": 1},
        {"year": 2021, "study_count": 2},
    ]
    assert alzheimers["organ_affinity"][0]["organ"] == "Brain"
    assert fallback["gene_distribution"][0]["association_source"] == "UniProt"


def test_load_disease_intelligence_upserts_json_payloads() -> None:
    executed: list[tuple[str, object]] = []

    class FakeCursor:
        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, query: str, params: object | None = None) -> None:
            executed.append((query, params))

        def executemany(self, query: str, params: list[dict[str, object]]) -> None:
            executed.append((query, params))

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

    records = [
        {
            "disease_id": "alzheimers-disease",
            "disease_name": "Alzheimer's disease",
            "frequency_timeline": [{"year": 2020, "study_count": 1}],
            "gene_distribution": [{"gene_symbol": "FOO", "uniprot_id": "P11111", "association_score": 0.92}],
            "organ_affinity": [{"organ": "Brain", "value": 2}],
            "therapeutic_landscape": [{"chembl_id": "CHEMBL100", "bioactivity_status": "Active"}],
            "clinical_summary": "summary",
            "top_gene_uniprot_ids": ["P11111"],
        }
    ]

    loaded = load_disease_intelligence(FakeConnection(), records)

    assert loaded == 1
    query, params = executed[-1]
    assert "INSERT INTO disease_intelligence" in query
    payload = params[0]
    assert isinstance(payload["frequency_timeline"], Jsonb)
    assert payload["top_gene_uniprot_ids"] == ["P11111"]
