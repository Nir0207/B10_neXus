from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiseaseProgram:
    disease_query: str
    organ: str
    disease_id: str | None = None
    max_targets: int = 8
    max_studies_per_gene: int = 20


DEFAULT_DISEASE_PROGRAMS: tuple[DiseaseProgram, ...] = (
    DiseaseProgram(
        disease_query="Alzheimer disease",
        disease_id="MONDO_0004975",
        organ="brain",
        max_targets=6,
        max_studies_per_gene=20,
    ),
)
