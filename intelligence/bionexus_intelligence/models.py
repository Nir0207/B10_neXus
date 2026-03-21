from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GeneRecord:
    gene_symbol: str
    uniprot_id: str


@dataclass(frozen=True, slots=True)
class PathwayRecord:
    uniprot_id: str
    reactome_id: str
    pathway_name: str


@dataclass(frozen=True, slots=True)
class StudySnippet:
    accession: str
    title: str
    snippet: str
    publication_date: str


@dataclass(frozen=True, slots=True)
class OpenTargetsEvidence:
    target_symbol: str
    disease_name: str
    evidence_score: float


@dataclass(frozen=True, slots=True)
class ToolContext:
    gene: GeneRecord
    pathways: list[PathwayRecord]
    snippets: list[StudySnippet]
    opentargets: list[OpenTargetsEvidence]


@dataclass(frozen=True, slots=True)
class StudyPathwayContext:
    study: StudySnippet
    related_pathways: list[PathwayRecord]


@dataclass(frozen=True, slots=True)
class DiseaseTrendSnapshot:
    disease_id: str
    disease_name: str
    clinical_summary: str
    frequency_timeline: list[dict[str, Any]]
    gene_distribution: list[dict[str, Any]]
    organ_affinity: list[dict[str, Any]]
    therapeutic_landscape: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class VisualReport:
    chart_type: str
    title: str
    disease_id: str
    disease_name: str
    x_key: str
    y_key: str
    datasets: list[dict[str, Any]]
    clinical_summary: str
