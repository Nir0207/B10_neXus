from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import (
    DiseaseTrendSnapshot,
    GeneRecord,
    OpenTargetsEvidence,
    PathwayRecord,
    StudyPathwayContext,
    StudySnippet,
)


class LLMClient(Protocol):
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        ...


class StudyRepository(Protocol):
    def ensure_studies_table(self) -> None:
        ...

    def seed_studies_from_csv(self, csv_path: Path) -> int:
        ...

    def resolve_gene(self, gene_or_uniprot: str) -> GeneRecord | None:
        ...

    def fetch_pathways_for_uniprot(self, uniprot_id: str, *, limit: int) -> list[PathwayRecord]:
        ...

    def fetch_study_snippets(self, query: str, *, limit: int) -> list[StudySnippet]:
        ...

    def fetch_study_pathway_context(self, study_id: str, *, limit: int) -> StudyPathwayContext | None:
        ...

    def fetch_disease_trend_snapshot(self, disease_query: str) -> DiseaseTrendSnapshot | None:
        ...


class OpenTargetsRepository(Protocol):
    def find_evidence_for_gene(self, gene_symbol: str, *, limit: int) -> list[OpenTargetsEvidence]:
        ...
