from __future__ import annotations

import json
from pathlib import Path

from .attribution import with_data_source_attribution
from .gene_profiles import FeaturedGeneProfile, get_featured_gene_profile
from .interfaces import LLMClient, OpenTargetsRepository, StudyRepository
from .llm import LLMGenerationError
from .models import (
    DiseaseTrendSnapshot,
    OpenTargetsEvidence,
    PathwayRecord,
    StudyPathwayContext,
    StudySnippet,
    ToolContext,
    VisualReport,
)
from .organ_profiles import FeaturedOrganProfile, get_featured_organ_profile


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

        context = self._build_tool_context(
            gene,
            snippet_limit=self._rag_snippet_limit,
            evidence_limit=5,
        )
        if context is None:
            message = f"No UniProt-mapped record was found for `{gene.strip()}` in staging."
            return with_data_source_attribution(message, base_sources)

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

    def explain_gene(self, gene: str) -> str:
        default_sources = [
            "Source: UniProt/Postgres silver.proteins",
            "Source: Reactome/Postgres silver.pathways",
            "Source: Open Targets",
        ]

        context = self._build_tool_context(
            gene,
            snippet_limit=min(self._rag_snippet_limit, 2),
            evidence_limit=3,
        )
        if context is None:
            return self._explain_featured_gene_without_staging(gene, default_sources)

        prompt = _build_gene_overview_prompt(context)
        system_prompt = (
            "You are a biomedical assistant. Explain the target clearly for translational research users. "
            "Use only the supplied context and state uncertainty when evidence is limited."
        )

        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_gene_overview(context)

        return with_data_source_attribution(answer, default_sources)

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

    def summarize_organ_context(
        self,
        *,
        organ: str,
        question: str,
        history: list[str] | None = None,
        disease: str | None = None,
        medicine: str | None = None,
        gene: str | None = None,
    ) -> str:
        sources = [
            "Source: BioNexus organ atlas profiles",
            "Source: BioNexus featured gene profiles",
            "Source: Open Targets",
        ]
        organ_profile = get_featured_organ_profile(organ)
        if organ_profile is None:
            return with_data_source_attribution(
                f"I do not have a curated organ-atlas profile for `{organ.strip()}` yet.",
                sources,
            )

        gene_profile = get_featured_gene_profile(gene or organ_profile.primary_target)
        evidence = self._open_targets_repository.find_evidence_for_gene(
            gene_profile.gene_symbol if gene_profile is not None else organ_profile.primary_target,
            limit=3,
        )
        prompt = _build_organ_context_prompt(
            organ_profile=organ_profile,
            question=question,
            history=history,
            gene_profile=gene_profile,
            disease=disease,
            medicine=medicine,
            evidence=evidence,
        )
        system_prompt = (
            "You are a translational research assistant. Answer organ-atlas questions using only the supplied "
            "curated organ profile, featured-target profile, and target evidence."
        )

        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_organ_context(
                organ_profile=organ_profile,
                gene_profile=gene_profile,
                disease=disease,
                medicine=medicine,
                evidence=evidence,
            )

        return with_data_source_attribution(answer, sources)

    def summarize_discovery_context(
        self,
        *,
        question: str,
        history: list[str] | None = None,
        organ: str | None = None,
        gene: str | None = None,
        uniprot_id: str | None = None,
        disease: str | None = None,
        medicine: str | None = None,
    ) -> str:
        tool_context = self._build_tool_context(
            uniprot_id or gene,
            snippet_limit=3,
            evidence_limit=3,
        )
        organ_profile = get_featured_organ_profile(organ) if organ else None
        featured_profile = get_featured_gene_profile(uniprot_id or gene or "")

        sources: list[str] = []
        if organ_profile is not None:
            sources.append("Source: BioNexus organ atlas profiles")
        if disease or medicine:
            sources.append("Source: Neo4j discovery graph")
        if tool_context is not None:
            sources.extend(
                [
                    "Source: UniProt/Postgres silver.proteins",
                    "Source: Reactome/Postgres silver.pathways",
                    "Source: NCBI GEO/Postgres silver.ncbi_studies",
                    "Source: Open Targets",
                ]
            )
        elif featured_profile is not None:
            sources.extend(["Source: BioNexus featured gene profiles", "Source: Open Targets"])
        else:
            sources.append("Source: BioNexus featured gene profiles")

        prompt = _build_discovery_context_prompt(
            question=question,
            history=history,
            organ_profile=organ_profile,
            tool_context=tool_context,
            featured_profile=featured_profile,
            disease=disease,
            medicine=medicine,
        )
        system_prompt = (
            "You are a biomedical discovery assistant. Answer free-form follow-up questions using the supplied "
            "current BioNexus UI context and cite uncertainty when data is sparse."
        )

        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_discovery_context(
                organ_profile=organ_profile,
                tool_context=tool_context,
                featured_profile=featured_profile,
                disease=disease,
                medicine=medicine,
            )

        return with_data_source_attribution(answer, _dedupe_sources(sources))

    def render_visual_report(
        self,
        *,
        prompt: str,
        disease: str,
    ) -> VisualReport | None:
        snapshot = self._study_repository.fetch_disease_trend_snapshot(disease)
        if snapshot is None:
            return None

        system_prompt = (
            "You are a biomedical visual reasoning assistant. Prioritize visual reasoning. "
            "Return strict JSON only with keys chart_type, title, x_key, y_key, datasets, clinical_summary. "
            "Choose chart_type from line, bar, radar."
        )
        user_prompt = _build_visual_reasoning_prompt(snapshot=snapshot, prompt=prompt)

        try:
            raw_response = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
            return _parse_visual_report(snapshot, raw_response)
        except (LLMGenerationError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return _fallback_visual_report(snapshot=snapshot, prompt=prompt)

    def _explain_featured_gene_without_staging(
        self,
        gene: str,
        default_sources: list[str],
    ) -> str:
        profile = get_featured_gene_profile(gene)
        if profile is None:
            message = f"No UniProt-mapped record was found for `{gene.strip()}` in staging."
            return with_data_source_attribution(message, default_sources)

        evidence = self._open_targets_repository.find_evidence_for_gene(profile.gene_symbol, limit=3)
        prompt = _build_profile_only_gene_overview_prompt(profile, evidence)
        system_prompt = (
            "You are a biomedical assistant. Explain the target clearly for translational research users. "
            "If staging context is unavailable, use the supplied local profile and note that the answer is a "
            "featured-organ summary rather than a staged pathway summary."
        )

        sources = ["Source: BioNexus featured gene profiles", "Source: Open Targets"]
        try:
            answer = self._llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.1,
            )
        except LLMGenerationError:
            answer = _fallback_profile_only_gene_overview(profile, evidence)

        return with_data_source_attribution(answer, sources)

    def _build_tool_context(
        self,
        gene_or_uniprot: str | None,
        *,
        snippet_limit: int,
        evidence_limit: int,
    ) -> ToolContext | None:
        if gene_or_uniprot is None or not gene_or_uniprot.strip():
            return None

        resolved_gene = self._study_repository.resolve_gene(gene_or_uniprot)
        if resolved_gene is None:
            return None

        return ToolContext(
            gene=resolved_gene,
            pathways=self._study_repository.fetch_pathways_for_uniprot(
                resolved_gene.uniprot_id,
                limit=self._pathway_limit,
            ),
            snippets=self._study_repository.fetch_study_snippets(
                resolved_gene.gene_symbol,
                limit=snippet_limit,
            ),
            opentargets=self._open_targets_repository.find_evidence_for_gene(
                resolved_gene.gene_symbol,
                limit=evidence_limit,
            ),
        )


def _build_visual_reasoning_prompt(*, snapshot: DiseaseTrendSnapshot, prompt: str) -> str:
    return "\n".join(
        [
            f"User request: {prompt.strip()}",
            f"Disease: {snapshot.disease_name} ({snapshot.disease_id})",
            f"Clinical summary: {snapshot.clinical_summary}",
            f"Frequency timeline: {json.dumps(snapshot.frequency_timeline)}",
            f"Gene distribution: {json.dumps(snapshot.gene_distribution)}",
            f"Organ affinity: {json.dumps(snapshot.organ_affinity)}",
            "Return only a JSON object with the requested keys.",
        ]
    )


def _parse_visual_report(snapshot: DiseaseTrendSnapshot, raw_response: str) -> VisualReport:
    payload = json.loads(raw_response)
    return VisualReport(
        chart_type=str(payload["chart_type"]),
        title=str(payload["title"]),
        disease_id=snapshot.disease_id,
        disease_name=snapshot.disease_name,
        x_key=str(payload["x_key"]),
        y_key=str(payload["y_key"]),
        datasets=[dict(item) for item in payload["datasets"]],
        clinical_summary=str(payload["clinical_summary"]),
    )


def _fallback_visual_report(*, snapshot: DiseaseTrendSnapshot, prompt: str) -> VisualReport:
    normalized_prompt = prompt.strip().lower()
    if "tissue" in normalized_prompt or "organ" in normalized_prompt or "affinity" in normalized_prompt:
        return VisualReport(
            chart_type="radar",
            title=f"{snapshot.disease_name} Organ Affinity",
            disease_id=snapshot.disease_id,
            disease_name=snapshot.disease_name,
            x_key="organ",
            y_key="value",
            datasets=snapshot.organ_affinity,
            clinical_summary=snapshot.clinical_summary,
        )

    if "gene" in normalized_prompt or "target" in normalized_prompt:
        return VisualReport(
            chart_type="bar",
            title=f"{snapshot.disease_name} Gene Distribution",
            disease_id=snapshot.disease_id,
            disease_name=snapshot.disease_name,
            x_key="gene_symbol",
            y_key="association_score",
            datasets=snapshot.gene_distribution,
            clinical_summary=snapshot.clinical_summary,
        )

    return VisualReport(
        chart_type="line",
        title=f"{snapshot.disease_name} Study Frequency",
        disease_id=snapshot.disease_id,
        disease_name=snapshot.disease_name,
        x_key="year",
        y_key="study_count",
        datasets=snapshot.frequency_timeline,
        clinical_summary=snapshot.clinical_summary,
    )


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


def _build_gene_overview_prompt(context: ToolContext) -> str:
    pathways_block = _format_pathways(context.pathways[:3])
    opentargets_block = _format_opentargets(context.opentargets[:3])

    return (
        f"Gene: {context.gene.gene_symbol}\n"
        f"UniProt ID: {context.gene.uniprot_id}\n\n"
        "Task:\n"
        "1. Explain what this gene/protein is in plain biomedical terms.\n"
        "2. Summarize why it matters for disease biology or therapeutics.\n"
        "3. Mention up to 2 pathway signals from the supplied context.\n\n"
        f"Reactome pathways:\n{pathways_block}\n\n"
        f"Open Targets evidence:\n{opentargets_block}\n"
    )


def _build_profile_only_gene_overview_prompt(
    profile: FeaturedGeneProfile,
    evidence: list[OpenTargetsEvidence],
) -> str:
    uniprot_line = f"UniProt ID: {profile.uniprot_id}\n" if profile.uniprot_id else ""
    opentargets_block = _format_opentargets(evidence[:3])

    return (
        f"Gene: {profile.gene_symbol}\n"
        f"Canonical name: {profile.canonical_name}\n"
        f"{uniprot_line}"
        "Context type: Featured BioNexus organ-atlas profile (staging mapping unavailable)\n\n"
        "Known profile summary:\n"
        f"- {profile.summary}\n"
        f"- {profile.translational_relevance}\n\n"
        "Task:\n"
        "1. Explain what this gene/protein is in plain biomedical terms.\n"
        "2. State why it matters translationally.\n"
        "3. Mention any disease signals from the supplied evidence.\n"
        "4. Note that this answer is using local featured-target knowledge because staging mapping is absent.\n\n"
        f"Open Targets evidence:\n{opentargets_block}\n"
    )


def _build_organ_context_prompt(
    *,
    organ_profile: FeaturedOrganProfile,
    question: str,
    history: list[str] | None,
    gene_profile: FeaturedGeneProfile | None,
    disease: str | None,
    medicine: str | None,
    evidence: list[OpenTargetsEvidence],
) -> str:
    return (
        f"User question: {question.strip()}\n\n"
        f"Organ: {organ_profile.label}\n"
        f"Atlas focus: {organ_profile.focus}\n"
        f"Primary target: {organ_profile.primary_target}\n"
        f"Expression signal: {organ_profile.expression}\n"
        f"Reference p-value: {organ_profile.p_value}\n"
        f"Key risk: {organ_profile.key_risk}\n\n"
        f"Featured target profile:\n{_format_featured_gene_profile(gene_profile)}\n\n"
        f"Current discovery graph context:\n{_format_discovery_triplet(disease=disease, medicine=medicine)}\n\n"
        f"Open Targets evidence:\n{_format_opentargets(evidence)}\n\n"
        f"Recent conversation:\n{_format_history(history)}\n\n"
        "Task:\n"
        "1. Answer the user's question directly.\n"
        "2. Explain the organ program focus in plain biomedical language.\n"
        "3. Tie the answer to the primary target and the key translational risk.\n"
        "4. Mention current disease or medicine context when available.\n"
    )


def _build_discovery_context_prompt(
    *,
    question: str,
    history: list[str] | None,
    organ_profile: FeaturedOrganProfile | None,
    tool_context: ToolContext | None,
    featured_profile: FeaturedGeneProfile | None,
    disease: str | None,
    medicine: str | None,
) -> str:
    organ_block = (
        f"{organ_profile.label}: focus={organ_profile.focus}, primary_target={organ_profile.primary_target}, "
        f"key_risk={organ_profile.key_risk}"
        if organ_profile is not None
        else "- No organ profile provided"
    )
    target_block = (
        _build_gene_overview_prompt(tool_context)
        if tool_context is not None
        else _format_featured_gene_profile(featured_profile)
    )
    pathway_block = _format_pathways(tool_context.pathways[:3]) if tool_context is not None else "- None"
    snippet_block = _format_snippets(tool_context.snippets[:2]) if tool_context is not None else "- None"
    evidence_block = _format_opentargets(tool_context.opentargets[:3]) if tool_context is not None else "- None"

    return (
        f"User question: {question.strip()}\n\n"
        f"Organ context:\n{organ_block}\n\n"
        f"Current discovery graph context:\n{_format_discovery_triplet(disease=disease, medicine=medicine)}\n\n"
        f"Current target context:\n{target_block}\n\n"
        f"Pathway context:\n{pathway_block}\n\n"
        f"Study context:\n{snippet_block}\n\n"
        f"Evidence context:\n{evidence_block}\n\n"
        f"Recent conversation:\n{_format_history(history)}\n\n"
        "Task:\n"
        "1. Answer the user's question directly.\n"
        "2. Use current organ, gene, disease, and medicine context when available.\n"
        "3. Explain translational relevance and one practical next step.\n"
        "4. State uncertainty when the current graph or staging data is sparse.\n"
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


def _format_featured_gene_profile(profile: FeaturedGeneProfile | None) -> str:
    if profile is None:
        return "- No featured target profile available"

    uniprot_line = f" UniProt {profile.uniprot_id}." if profile.uniprot_id else ""
    return (
        f"- {profile.gene_symbol}: {profile.canonical_name}.{uniprot_line}\n"
        f"- Summary: {profile.summary}\n"
        f"- Translational relevance: {profile.translational_relevance}"
    )


def _format_discovery_triplet(*, disease: str | None, medicine: str | None) -> str:
    if disease is None and medicine is None:
        return "- No active disease or medicine nodes are in the current graph selection"

    parts: list[str] = []
    if disease:
        parts.append(f"disease={disease}")
    if medicine:
        parts.append(f"medicine={medicine}")
    return f"- {'; '.join(parts)}"


def _format_history(history: list[str] | None) -> str:
    if not history:
        return "- No recent conversation history"
    return "\n".join(f"- {entry}" for entry in history[-6:])


def _dedupe_sources(sources: list[str]) -> list[str]:
    return list(dict.fromkeys(sources))


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


def _fallback_gene_overview(context: ToolContext) -> str:
    pathways = ", ".join(item.pathway_name for item in context.pathways[:2]) or "no mapped pathways"
    evidence = (
        f" Open Targets evidence links it to {context.opentargets[0].disease_name} "
        f"(score {context.opentargets[0].evidence_score:.2f})."
        if context.opentargets
        else ""
    )
    return (
        f"Ollama is currently unavailable. Deterministic fallback: {context.gene.gene_symbol} "
        f"is represented in BioNexus as UniProt {context.gene.uniprot_id}. "
        f"Current pathway context: {pathways}.{evidence}"
    )


def _fallback_profile_only_gene_overview(
    profile: FeaturedGeneProfile,
    evidence: list[OpenTargetsEvidence],
) -> str:
    evidence_text = (
        f" Open Targets currently links {profile.gene_symbol} to {evidence[0].disease_name} "
        f"(score {evidence[0].evidence_score:.2f})."
        if evidence
        else ""
    )
    uniprot_text = f" It maps to UniProt {profile.uniprot_id}." if profile.uniprot_id else ""
    return (
        f"Ollama is currently unavailable. Deterministic fallback: {profile.gene_symbol} is "
        f"{profile.canonical_name}. {profile.summary} {profile.translational_relevance}{uniprot_text}"
        " This answer is using the local featured-target profile because staging does not yet contain a "
        f"UniProt-mapped row for {profile.gene_symbol}.{evidence_text}"
    )


def _fallback_organ_context(
    *,
    organ_profile: FeaturedOrganProfile,
    gene_profile: FeaturedGeneProfile | None,
    disease: str | None,
    medicine: str | None,
    evidence: list[OpenTargetsEvidence],
) -> str:
    gene_text = (
        f" Primary target {gene_profile.gene_symbol}: {gene_profile.summary}"
        if gene_profile is not None
        else f" Primary target is {organ_profile.primary_target}."
    )
    graph_text = ""
    if disease or medicine:
        graph_parts = [part for part in [disease, medicine] if part]
        graph_text = f" Current graph context links this organ view to {' and '.join(graph_parts)}."
    evidence_text = (
        f" Open Targets highlights {evidence[0].disease_name} with score {evidence[0].evidence_score:.2f}."
        if evidence
        else ""
    )
    return (
        f"Ollama is currently unavailable. Deterministic fallback: the {organ_profile.label} atlas is centered on "
        f"{organ_profile.focus}, with expression signal {organ_profile.expression} and key risk "
        f"{organ_profile.key_risk}.{gene_text}{graph_text}{evidence_text}"
    )


def _fallback_discovery_context(
    *,
    organ_profile: FeaturedOrganProfile | None,
    tool_context: ToolContext | None,
    featured_profile: FeaturedGeneProfile | None,
    disease: str | None,
    medicine: str | None,
) -> str:
    context_parts: list[str] = []
    if organ_profile is not None:
        context_parts.append(
            f"{organ_profile.label} context is focused on {organ_profile.focus} with key risk {organ_profile.key_risk}"
        )
    if tool_context is not None:
        pathways = ", ".join(item.pathway_name for item in tool_context.pathways[:2]) or "no mapped pathways"
        context_parts.append(
            f"{tool_context.gene.gene_symbol} maps to UniProt {tool_context.gene.uniprot_id} and pathways {pathways}"
        )
        if tool_context.opentargets:
            top = tool_context.opentargets[0]
            context_parts.append(
                f"Open Targets links it to {top.disease_name} (score {top.evidence_score:.2f})"
            )
    elif featured_profile is not None:
        context_parts.append(
            f"{featured_profile.gene_symbol} is {featured_profile.canonical_name} and {featured_profile.translational_relevance.lower()}"
        )
    if disease or medicine:
        linked = " and ".join(part for part in [disease, medicine] if part)
        context_parts.append(f"current graph nodes include {linked}")

    summary = ". ".join(context_parts) if context_parts else "the current BioNexus view has limited structured context"
    return (
        "Ollama is currently unavailable. Deterministic fallback: "
        f"{summary}. Recommended next step: review the active organ atlas, validate the highlighted target, "
        "and compare the current disease-medicine link against staged pathway evidence."
    )
