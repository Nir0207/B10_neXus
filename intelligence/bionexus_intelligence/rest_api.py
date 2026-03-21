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
    "WHAT",
    "HAVE",
    "WITH",
    "THIS",
    "THAT",
    "FROM",
    "LEADS",
    "EXPLAIN",
    "PATHWAY",
    "STUDY",
}


class IntelligenceQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    organ: str | None = Field(default=None, max_length=32)
    gene: str | None = Field(default=None, max_length=64)
    uniprot_id: str | None = Field(default=None, max_length=15)
    disease: str | None = Field(default=None, max_length=128)
    medicine: str | None = Field(default=None, max_length=128)
    study_id: str | None = Field(default=None, max_length=32)


class IntelligenceQueryResponse(BaseModel):
    reply: str
    mode: Literal["drug_leads", "gene_overview", "pathway", "context_fallback"]
    resolved_entity: str | None = None
    sources: list[str] = Field(default_factory=list)


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
        mode, entity, reply = _resolve_query(service, payload)
        sources = _extract_sources(reply)
        return IntelligenceQueryResponse(
            reply=reply,
            mode=mode,
            resolved_entity=entity,
            sources=sources,
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
) -> tuple[Literal["drug_leads", "gene_overview", "pathway", "context_fallback"], str | None, str]:
    study_id = payload.study_id or _extract_study_id(payload.prompt)
    if study_id:
        return "pathway", study_id, service.explain_pathway(study_id)

    gene_hint = payload.uniprot_id or payload.gene or _extract_gene_hint(payload.prompt)
    if gene_hint:
        if _is_gene_overview_prompt(payload.prompt):
            return "gene_overview", gene_hint, service.explain_gene(gene_hint)
        return "drug_leads", gene_hint, service.get_drug_leads(gene_hint)

    return "context_fallback", None, _build_context_fallback(payload)


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
    normalized = prompt.strip().lower()
    return normalized.startswith("what is ") or normalized.startswith("who is ")


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
