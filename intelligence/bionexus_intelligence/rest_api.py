from __future__ import annotations

import logging
import re
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .config import Settings
from .server import create_intelligence_service
from .service import IntelligenceService

logger = logging.getLogger(__name__)

_GEO_ACCESSION_PATTERN = re.compile(r"\b(GSE\d{2,})\b", re.IGNORECASE)
_GENE_PATTERN = re.compile(r"\b([A-Z0-9-]{4,15})\b")
_GENE_STOPWORDS = {
    "ABOUT",
    "ATLAS",
    "CURRENT",
    "DESCRIBE",
    "DOES",
    "EXPLAIN",
    "FOCUS",
    "FROM",
    "FUNCTION",
    "GENE",
    "GRAPH",
    "HAVE",
    "HELP",
    "IMPACT",
    "KNOW",
    "LEAD",
    "LEADS",
    "LOOK",
    "MATTER",
    "MEAN",
    "MEDICINE",
    "NETWORK",
    "NEXT",
    "ORGAN",
    "OVERVIEW",
    "PATHWAY",
    "PLEASE",
    "PROGRAM",
    "PROTEIN",
    "RISK",
    "ROLE",
    "SAFETY",
    "SHOULD",
    "SHOW",
    "SIGNAL",
    "STAGED",
    "STUDY",
    "TARGET",
    "THAT",
    "THIS",
    "TEST",
    "TREATMENT",
    "TRIAL",
    "UNDERSTAND",
    "WHAT",
    "WHY",
    "WITH",
}
_GENE_OVERVIEW_PREFIXES = (
    "what is ",
    "who is ",
    "tell me about ",
    "explain ",
    "describe ",
    "what does ",
    "why does ",
    "why is ",
    "role of ",
    "function of ",
)
_DRUG_LEAD_KEYWORDS = ("lead", "drug", "therapy", "therapeutic", "treat", "compound", "intervention", "candidate")
_ORGAN_KEYWORDS = ("organ atlas", "current organ", "this organ", "organ focus", "organ program", "atlas")
_REFERENTIAL_GENE_KEYWORDS = (
    "this target",
    "this gene",
    "this protein",
    "what about this",
    "help me understand this",
)
_TREND_KEYWORDS = ("trend", "trends", "historical", "rise", "frequency", "timeline", "over time")
_TREND_DISEASE_PATTERN = re.compile(
    r"(?:for|of|about)\s+([A-Za-z0-9' -]{3,80}?)(?:\s+genes?\b|\s+targets?\b|\s+trend|\s+timeline|$)",
    re.IGNORECASE,
)


class IntelligenceHistoryTurn(BaseModel):
    role: Literal["assistant", "user"]
    text: str = Field(..., min_length=1, max_length=2000)


class IntelligenceQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    organ: str | None = Field(default=None, max_length=32)
    gene: str | None = Field(default=None, max_length=64)
    uniprot_id: str | None = Field(default=None, max_length=15)
    disease: str | None = Field(default=None, max_length=128)
    medicine: str | None = Field(default=None, max_length=128)
    study_id: str | None = Field(default=None, max_length=32)
    history: list[IntelligenceHistoryTurn] = Field(default_factory=list, max_length=12)


class IntelligenceQueryResponse(BaseModel):
    reply: str
    mode: Literal["drug_leads", "gene_overview", "pathway", "organ_overview", "discovery_context", "context_fallback", "visual_report"]
    resolved_entity: str | None = None
    sources: list[str] = Field(default_factory=list)
    visual_payload: VisualPayload | None = None


class VisualPayload(BaseModel):
    chart_type: Literal["line", "bar", "radar"]
    title: str
    disease_id: str
    disease_name: str
    x_key: str
    y_key: str
    datasets: list[dict[str, object]] = Field(default_factory=list)
    clinical_summary: str


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    service = create_intelligence_service(resolved_settings)
    _initialize_service(service, resolved_settings)

    app = FastAPI(
        title="BioNexus Intelligence API",
        description="REST bridge for the BioNexus intelligence service.",
    )
    app.state.intelligence_service = service

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/intelligence/query", response_model=IntelligenceQueryResponse)
    def query(payload: IntelligenceQueryRequest) -> IntelligenceQueryResponse:
        mode, entity, reply, visual_payload = _resolve_query(service, payload)
        sources = _extract_sources(reply)
        return IntelligenceQueryResponse(
            reply=reply,
            mode=mode,
            resolved_entity=entity,
            sources=sources,
            visual_payload=visual_payload,
        )

    return app


def _initialize_service(service: IntelligenceService, settings: Settings) -> None:
    try:
        seeded_rows = service.initialize(settings.seed_study_csv_path)
        logger.info("Initialized staging study table with %d row(s).", seeded_rows)
    except Exception as exc:  # pragma: no cover - runtime resilience path
        logger.warning("Staging initialization skipped: %s", exc)


def _resolve_query(
    service: IntelligenceService,
    payload: IntelligenceQueryRequest,
) -> tuple[
    Literal["drug_leads", "gene_overview", "pathway", "organ_overview", "discovery_context", "context_fallback", "visual_report"],
    str | None,
    str,
    VisualPayload | None,
]:
    history = _history_lines(payload.history)
    study_id = payload.study_id or _extract_study_id(payload.prompt)
    if study_id:
        return "pathway", study_id, service.explain_pathway(study_id), None

    trend_disease = payload.disease or _extract_trend_disease(payload.prompt)
    if trend_disease and _is_trend_prompt(payload.prompt.strip().lower()):
        report = service.render_visual_report(prompt=payload.prompt, disease=trend_disease)
        if report is not None:
            visual_reply = (
                f"{report.clinical_summary}\n\n"
                "Data Source Attribution: Source: Postgres disease_intelligence; "
                "Source: NCBI GEO; Source: UniProt; Source: Open Targets; Source: ChEMBL"
            )
            return (
                "visual_report",
                report.disease_id,
                visual_reply,
                VisualPayload(
                    chart_type=report.chart_type,
                    title=report.title,
                    disease_id=report.disease_id,
                    disease_name=report.disease_name,
                    x_key=report.x_key,
                    y_key=report.y_key,
                    datasets=report.datasets,
                    clinical_summary=report.clinical_summary,
                ),
            )

    prompt_gene = _extract_gene_hint(payload.prompt)
    history_gene = _extract_gene_hint_from_history(history)
    context_gene = payload.uniprot_id or payload.gene
    gene_hint = prompt_gene or context_gene or history_gene
    normalized_prompt = payload.prompt.strip().lower()

    if gene_hint:
        if _is_drug_lead_prompt(normalized_prompt):
            return "drug_leads", gene_hint, service.get_drug_leads(gene_hint), None
        if _is_gene_overview_prompt(normalized_prompt) or _is_referential_gene_prompt(normalized_prompt):
            return "gene_overview", gene_hint, service.explain_gene(gene_hint), None
        if _has_contextual_state(payload):
            return (
                "discovery_context",
                gene_hint,
                service.summarize_discovery_context(
                    question=payload.prompt,
                    history=history,
                    organ=payload.organ,
                    gene=payload.gene,
                    uniprot_id=payload.uniprot_id,
                    disease=payload.disease,
                    medicine=payload.medicine,
                ),
                None,
            )
        return "gene_overview", gene_hint, service.explain_gene(gene_hint), None

    if payload.organ and (_is_organ_prompt(normalized_prompt) or not _has_contextual_state(payload)):
        return (
            "organ_overview",
            payload.organ,
            service.summarize_organ_context(
                organ=payload.organ,
                question=payload.prompt,
                history=history,
                disease=payload.disease,
                medicine=payload.medicine,
                gene=payload.gene or payload.uniprot_id,
            ),
            None,
        )

    if _has_contextual_state(payload):
        return (
            "discovery_context",
            payload.gene or payload.uniprot_id or payload.organ,
            service.summarize_discovery_context(
                question=payload.prompt,
                history=history,
                organ=payload.organ,
                gene=payload.gene,
                uniprot_id=payload.uniprot_id,
                disease=payload.disease,
                medicine=payload.medicine,
            ),
            None,
        )

    return "context_fallback", None, _build_context_fallback(payload), None


def _extract_study_id(prompt: str) -> str | None:
    match = _GEO_ACCESSION_PATTERN.search(prompt)
    if not match:
        return None
    return match.group(1).upper()


def _extract_gene_hint(prompt: str) -> str | None:
    for token in _GENE_PATTERN.findall(prompt.upper()):
        if token.startswith("GSE"):
            continue
        if token in _GENE_STOPWORDS:
            continue
        if 4 <= len(token) <= 15:
            return token
    return None


def _extract_gene_hint_from_history(history: list[str]) -> str | None:
    for entry in reversed(history):
        hint = _extract_gene_hint(entry)
        if hint is not None:
            return hint
    return None


def _build_context_fallback(payload: IntelligenceQueryRequest) -> str:
    context_parts = [
        f"organ={payload.organ}" if payload.organ else "",
        f"gene={payload.gene or payload.uniprot_id}" if (payload.gene or payload.uniprot_id) else "",
        f"disease={payload.disease}" if payload.disease else "",
        f"medicine={payload.medicine}" if payload.medicine else "",
    ]
    normalized_context = ", ".join(part for part in context_parts if part)

    if normalized_context:
        return (
            "I need a gene symbol, UniProt ID, or GEO accession to invoke the full intelligence workflow. "
            f"Current UI context: {normalized_context}. "
            "Ask about the active gene or provide a study accession such as GSE12345."
        )

    return (
        "I need a gene symbol, UniProt ID, or GEO accession to invoke the intelligence workflow. "
        "Ask about a target such as EGFR or provide a study accession such as GSE12345."
    )


def _extract_sources(reply: str) -> list[str]:
    marker = "Data Source Attribution:"
    if marker not in reply:
        return []

    _, _, tail = reply.partition(marker)
    return [item.strip() for item in tail.split(";") if item.strip()]


def _is_gene_overview_prompt(prompt: str) -> bool:
    return prompt.startswith(_GENE_OVERVIEW_PREFIXES)


def _is_drug_lead_prompt(prompt: str) -> bool:
    return any(keyword in prompt for keyword in _DRUG_LEAD_KEYWORDS)


def _is_organ_prompt(prompt: str) -> bool:
    return any(keyword in prompt for keyword in _ORGAN_KEYWORDS)


def _is_referential_gene_prompt(prompt: str) -> bool:
    return any(keyword in prompt for keyword in _REFERENTIAL_GENE_KEYWORDS)


def _is_trend_prompt(prompt: str) -> bool:
    return any(keyword in prompt for keyword in _TREND_KEYWORDS)


def _extract_trend_disease(prompt: str) -> str | None:
    match = _TREND_DISEASE_PATTERN.search(prompt)
    if match is None:
        return None
    value = match.group(1).strip()
    return value if value else None


def _has_contextual_state(payload: IntelligenceQueryRequest) -> bool:
    return any([payload.organ, payload.gene, payload.uniprot_id, payload.disease, payload.medicine])


def _history_lines(history: list[IntelligenceHistoryTurn]) -> list[str]:
    return [f"{turn.role}: {turn.text.strip()}" for turn in history if turn.text.strip()]


app = create_app()


def main() -> None:
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    uvicorn.run(
        "bionexus_intelligence.rest_api:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    main()
