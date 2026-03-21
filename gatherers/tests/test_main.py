from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from disease_programs import DiseaseProgram

_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
_SPEC = importlib.util.spec_from_file_location("gatherers_main", _MAIN_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load gatherers/main.py for tests.")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
gather_disease_program = _MODULE.gather_disease_program


class _FakeUniProtGatherer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def fetch(self, gene: str, *, organism: str) -> dict[str, object]:
        self.calls.append((gene, organism))
        return {"results": [{"primaryAccession": gene}]}


class _FakeNCBIGatherer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    async def fetch_geo_studies(
        self,
        gene: str,
        *,
        organ: str,
        max_records: int,
    ) -> dict[str, object]:
        self.calls.append((gene, organ, max_records))
        return {"result": {"uids": []}}


class _FakeOpenTargetsGatherer:
    def __init__(self) -> None:
        self.fetch_calls: list[tuple[str, str, str | None]] = []

    async def resolve_disease_id(self, query_string: str) -> tuple[str, str]:
        return "MONDO_0004975", query_string

    async def fetch_disease_evidence(
        self,
        disease_id: str,
        *,
        organ: str,
        stem: str | None = None,
    ) -> dict[str, object]:
        self.fetch_calls.append((disease_id, organ, stem))
        return {
            "data": {
                "disease": {
                    "associatedTargets": {
                        "rows": [
                            {"target": {"approvedSymbol": "PSEN1"}},
                            {"target": {"approvedSymbol": "APP"}},
                        ]
                    }
                }
            }
        }

    @staticmethod
    def extract_top_target_genes(payload: dict[str, object], *, limit: int) -> list[str]:
        del payload
        return ["PSEN1", "APP"][:limit]


@pytest.mark.asyncio
async def test_gather_disease_program_fetches_downstream_sources() -> None:
    uniprot = _FakeUniProtGatherer()
    ncbi = _FakeNCBIGatherer()
    opentargets = _FakeOpenTargetsGatherer()

    genes = await gather_disease_program(
        DiseaseProgram(
            disease_query="Alzheimer disease",
            disease_id="MONDO_0004975",
            organ="brain",
            max_targets=2,
            max_studies_per_gene=15,
        ),
        uniprot=uniprot,
        opentargets=opentargets,
        ncbi=ncbi,
    )

    assert genes == ["PSEN1", "APP"]
    assert uniprot.calls == [("PSEN1", "brain"), ("APP", "brain")]
    assert ncbi.calls == [("PSEN1", "brain", 15), ("APP", "brain", 15)]
