from __future__ import annotations

from pathlib import Path

from .attribution import with_data_source_attribution
from .interfaces import LLMClient, OpenTargetsRepository, StudyRepository
from .llm import LLMGenerationError
from .models import OpenTargetsEvidence, PathwayRecord, StudyPathwayContext, StudySnippet, ToolContext


class IntelligenceService:
    """Use-case layer for BioNexus FastMCP tools."""

    def __init__(
        self,
        *,
        study_repository: StudyRepository,
        open_targets_repository: OpenTargetsRepository,
        llm_client: LLMClient,
        rag_snippet_limit: int,
        pathway_limit: int,
    ):
        self._study_repository = study_repository
        self._open_targets_repository = open_targets_repository
        self._llm_client = llm_client
        self._rag_snippet_limit = rag_snippet_limit
        self._pathway_limit = pathway_limit

    def initialize(self, seed_csv_path: Path) -> int:
        self._study_repository.ensure_studies_table()
        return self._study_repository.seed_studies_from_csv(seed_csv_path)

    def get_drug_leads(self, gene: str) -> str:
        base_sources = [
            "Source: UniProt/Postgres silver.proteins",
            "Source: Reactome/Postgres silver.pathways",
            "Source: NCBI GEO/Postgres silver.ncbi_studies",
            "Source: Open Targets",
        ]

        resolved_gene = self._study_repository.resolve_gene(gene)
        if not resolved_gene:
            message = f"No UniProt-mapped record was found for `{gene.strip()}` in staging."
            return with_data_source_attribution(message, base_sources)

        context = ToolContext(
            gene=resolved_gene,
            pathways=self._study_repository.fetch_pathways_for_uniprot(
                resolved_gene.uniprot_id,
                limit=self._pathway_limit,
            ),
            snippets=self._study_repository.fetch_study_snippets(
                resolved_gene.gene_symbol,
                limit=self._rag_snippet_limit,
            ),
            opentargets=self._open_targets_repository.find_evidence_for_gene(
                resolved_gene.gene_symbol,
                limit=5,
            ),
        )

        prompt = _build_drug_lead_prompt(context)
        system_prompt = (
            "You are a biomedical assistant. Rank hypotheses conservatively. "
            "Use only provided context and state uncertainty when evidence is weak."
        )

        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_drug_leads(context)

        return with_data_source_attribution(answer, base_sources)

    def explain_pathway(self, study_id: str) -> str:
        base_sources = [
            "Source: NCBI GEO/Postgres silver.ncbi_studies",
            "Source: Reactome/Postgres silver.pathways",
            "Source: UniProt/Postgres silver.proteins",
        ]

        context = self._study_repository.fetch_study_pathway_context(
            study_id.strip(),
            limit=self._pathway_limit,
        )
        if context is None:
            return with_data_source_attribution(
                f"Study `{study_id.strip()}` was not found in staging study metadata.",
                base_sources,
            )

        prompt = _build_pathway_prompt(context)
        system_prompt = (
            "You explain pathway mechanisms for translational research. "
            "Ground every statement in the supplied study and pathway snippets."
        )

        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_pathway_explanation(context)

        return with_data_source_attribution(answer, base_sources)


def _build_drug_lead_prompt(context: ToolContext) -> str:
    pathways_block = _format_pathways(context.pathways)
    snippets_block = _format_snippets(context.snippets)
    opentargets_block = _format_opentargets(context.opentargets)

    return (
        f"Gene: {context.gene.gene_symbol}\n"
        f"UniProt ID: {context.gene.uniprot_id}\n\n"
        "Task:\n"
        "1. Suggest up to 3 actionable drug leads or pathway interventions.\n"
        "2. For each lead provide rationale tied to evidence snippets.\n"
        "3. Add confidence level (High/Medium/Low) and one key risk.\n\n"
        f"Reactome pathways:\n{pathways_block}\n\n"
        f"RAG study snippets:\n{snippets_block}\n\n"
        f"Open Targets evidence:\n{opentargets_block}\n"
    )


def _build_pathway_prompt(context: StudyPathwayContext) -> str:
    pathway_block = _format_pathways(context.related_pathways)
    return (
        f"Study ID: {context.study.accession}\n"
        f"Title: {context.study.title}\n"
        f"Summary snippet: {context.study.snippet}\n\n"
        "Task:\n"
        "1. Explain plausible pathways connected to this study.\n"
        "2. Use only pathways listed in context.\n"
        "3. Include one sentence on translational relevance.\n\n"
        f"Candidate pathways:\n{pathway_block}\n"
    )


def _format_pathways(pathways: list[PathwayRecord]) -> str:
    if not pathways:
        return "- None found in staging pathway map"

    return "\n".join(
        f"- {row.reactome_id} ({row.uniprot_id}): {row.pathway_name}"
        for row in pathways
    )


def _format_snippets(snippets: list[StudySnippet]) -> str:
    if not snippets:
        return "- No matching study snippets were found"

    lines: list[str] = []
    for row in snippets:
        compact = " ".join(row.snippet.split())[:320]
        lines.append(f"- {row.accession} ({row.publication_date}): {compact}")
    return "\n".join(lines)


def _format_opentargets(evidence: list[OpenTargetsEvidence]) -> str:
    if not evidence:
        return "- No direct target rows available in the current Open Targets snapshot"

    return "\n".join(
        f"- {row.target_symbol} vs {row.disease_name}: score={row.evidence_score:.3f}"
        for row in evidence
    )


def _fallback_drug_leads(context: ToolContext) -> str:
    pathways = ", ".join(item.pathway_name for item in context.pathways[:3]) or "no mapped pathways"
    return (
        f"Ollama is currently unavailable. Deterministic fallback: {context.gene.gene_symbol} "
        f"(UniProt {context.gene.uniprot_id}) maps to {pathways}. "
        "Prioritize manual review of top pathway-linked compounds and validate against recent NCBI studies."
    )


def _fallback_pathway_explanation(context: StudyPathwayContext) -> str:
    if not context.related_pathways:
        return (
            f"Ollama is currently unavailable. Deterministic fallback: study {context.study.accession} has "
            "no linked Reactome pathways in current staging tables."
        )

    top = context.related_pathways[0]
    return (
        f"Ollama is currently unavailable. Deterministic fallback: study {context.study.accession} "
        f"is linked to Reactome pathway {top.reactome_id} ({top.pathway_name}) through UniProt "
        f"target {top.uniprot_id}."
    )
