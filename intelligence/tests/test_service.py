from __future__ import annotations

from pathlib import Path

from bionexus_intelligence.llm import LLMGenerationError
from bionexus_intelligence.models import (
    GeneRecord,
    OpenTargetsEvidence,
    PathwayRecord,
    StudyPathwayContext,
    StudySnippet,
)
from bionexus_intelligence.service import IntelligenceService


class FakeStudyRepo:
    def __init__(self) -> None:
        self.initialized = False
        self.seeded_path: Path | None = None

    def ensure_studies_table(self) -> None:
        self.initialized = True

    def seed_studies_from_csv(self, csv_path: Path) -> int:
        self.seeded_path = csv_path
        return 3

    def resolve_gene(self, gene_or_uniprot: str) -> GeneRecord | None:
        if gene_or_uniprot.upper() in {"BRCA1", "P38398", "GRIN2B"}:
            if gene_or_uniprot.upper() == "GRIN2B":
                return GeneRecord(gene_symbol="GRIN2B", uniprot_id="Q13224")
            return GeneRecord(gene_symbol="BRCA1", uniprot_id="P38398")
        return None

    def fetch_pathways_for_uniprot(self, uniprot_id: str, *, limit: int) -> list[PathwayRecord]:
        assert uniprot_id in {"P38398", "Q13224"}
        assert limit > 0
        if uniprot_id == "Q13224":
            return [
                PathwayRecord(
                    uniprot_id="Q13224",
                    reactome_id="R-HSA-112316",
                    pathway_name="Neuronal System",
                )
            ]
        return [
            PathwayRecord(
                uniprot_id="P38398",
                reactome_id="R-HSA-5685938",
                pathway_name="HDR through Homologous Recombination",
            )
        ]

    def fetch_study_snippets(self, query: str, *, limit: int) -> list[StudySnippet]:
        assert query in {"BRCA1", "GRIN2B"}
        assert limit > 0
        if query == "GRIN2B":
            return []
        return [
            StudySnippet(
                accession="GSE267911",
                title="BRCA1 sensitivity study",
                snippet="BRCA1-altered cells showed stronger response patterns.",
                publication_date="2026/03/18",
            )
        ]

    def fetch_study_pathway_context(self, study_id: str, *, limit: int) -> StudyPathwayContext | None:
        if study_id != "GSE267911":
            return None
        return StudyPathwayContext(
            study=StudySnippet(
                accession="GSE267911",
                title="BRCA1 sensitivity study",
                snippet="Signals around BRCA1 and DNA repair pathways were observed.",
                publication_date="2026/03/18",
            ),
            related_pathways=[
                PathwayRecord(
                    uniprot_id="P38398",
                    reactome_id="R-HSA-5685938",
                    pathway_name="HDR through Homologous Recombination",
                )
            ],
        )


class FakeOpenTargetsRepo:
    def find_evidence_for_gene(self, gene_symbol: str, *, limit: int) -> list[OpenTargetsEvidence]:
        assert gene_symbol in {"BRCA1", "GRIN2B"}
        return [
            OpenTargetsEvidence(
                target_symbol=gene_symbol,
                disease_name="Breast carcinoma" if gene_symbol == "BRCA1" else "Neurodevelopmental disorder",
                evidence_score=0.81 if gene_symbol == "BRCA1" else 0.62,
            )
        ]


class SparseStudyRepo(FakeStudyRepo):
    def resolve_gene(self, gene_or_uniprot: str) -> GeneRecord | None:
        if gene_or_uniprot.upper() == "GRIN2B":
            return None
        return super().resolve_gene(gene_or_uniprot)


class GoodLLM:
    def generate(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        assert system_prompt
        assert user_prompt
        assert temperature == 0.1
        return "Ranked lead output"


class FailingLLM:
    def generate(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        raise LLMGenerationError("offline")


def _build_service(llm: GoodLLM | FailingLLM) -> IntelligenceService:
    return IntelligenceService(
        study_repository=FakeStudyRepo(),
        open_targets_repository=FakeOpenTargetsRepo(),
        llm_client=llm,
        rag_snippet_limit=4,
        pathway_limit=3,
    )


def _build_sparse_service(llm: GoodLLM | FailingLLM) -> IntelligenceService:
    return IntelligenceService(
        study_repository=SparseStudyRepo(),
        open_targets_repository=FakeOpenTargetsRepo(),
        llm_client=llm,
        rag_snippet_limit=4,
        pathway_limit=3,
    )


def test_initialize_bootstraps_staging_table() -> None:
    repo = FakeStudyRepo()
    service = IntelligenceService(
        study_repository=repo,
        open_targets_repository=FakeOpenTargetsRepo(),
        llm_client=GoodLLM(),
        rag_snippet_limit=4,
        pathway_limit=3,
    )

    seeded = service.initialize(Path("/tmp/studies.csv"))

    assert repo.initialized is True
    assert repo.seeded_path == Path("/tmp/studies.csv")
    assert seeded == 3


def test_get_drug_leads_includes_data_source_attribution() -> None:
    result = _build_service(GoodLLM()).get_drug_leads("BRCA1")

    assert "Ranked lead output" in result
    assert "Data Source Attribution:" in result
    assert "Source: Open Targets" in result


def test_get_drug_leads_handles_missing_uniprot_mapping() -> None:
    result = _build_service(GoodLLM()).get_drug_leads("UNKNOWN")

    assert "No UniProt-mapped record" in result
    assert "Data Source Attribution:" in result


def test_get_drug_leads_falls_back_when_ollama_fails() -> None:
    result = _build_service(FailingLLM()).get_drug_leads("BRCA1")

    assert "Deterministic fallback" in result
    assert "Data Source Attribution:" in result


def test_explain_pathway_includes_data_source_attribution() -> None:
    result = _build_service(GoodLLM()).explain_pathway("GSE267911")

    assert "Ranked lead output" in result
    assert "Data Source Attribution:" in result


def test_explain_pathway_handles_missing_study() -> None:
    result = _build_service(GoodLLM()).explain_pathway("MISSING_STUDY")

    assert "was not found" in result
    assert "Data Source Attribution:" in result


def test_explain_gene_includes_data_source_attribution() -> None:
    result = _build_service(GoodLLM()).explain_gene("GRIN2B")

    assert "Ranked lead output" in result
    assert "Data Source Attribution:" in result
    assert "Source: UniProt/Postgres silver.proteins" in result


def test_explain_gene_falls_back_when_ollama_fails() -> None:
    result = _build_service(FailingLLM()).explain_gene("GRIN2B")

    assert "Deterministic fallback" in result
    assert "Q13224" in result


def test_explain_gene_uses_featured_profile_when_staging_mapping_missing() -> None:
    result = _build_sparse_service(FailingLLM()).explain_gene("GRIN2B")

    assert "Glutamate Ionotropic Receptor NMDA Type Subunit 2B" in result
    assert "featured-target profile" in result
    assert "Source: BioNexus featured gene profiles" in result
