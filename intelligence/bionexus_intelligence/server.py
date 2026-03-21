from __future__ import annotations

import logging
from typing import Any

from .config import Settings
from .llm import OllamaClient
from .repositories import JsonOpenTargetsRepository, PostgresStudyRepository
from .service import IntelligenceService

try:
    from fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - guarded for environments without optional deps
    FastMCP = Any  # type: ignore[misc, assignment]
    _FASTMCP_IMPORT_ERROR: Exception | None = exc
else:
    _FASTMCP_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Thin adapter to keep FastMCP wiring separate from business logic."""

    def __init__(self, service: IntelligenceService):
        self._service = service

    def get_drug_leads(self, gene: str) -> str:
        return self._service.get_drug_leads(gene)

    def explain_pathway(self, study_id: str) -> str:
        return self._service.explain_pathway(study_id)


def create_intelligence_service(settings: Settings) -> IntelligenceService:
    return IntelligenceService(
        study_repository=PostgresStudyRepository(settings.pg_dsn),
        open_targets_repository=JsonOpenTargetsRepository(settings.opentargets_evidence_path),
        llm_client=OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        ),
        rag_snippet_limit=settings.rag_snippet_limit,
        pathway_limit=settings.pathway_limit,
    )


def create_mcp_server(settings: Settings | None = None) -> FastMCP:
    if _FASTMCP_IMPORT_ERROR is not None:
        raise RuntimeError(
            "fastmcp is required to run the intelligence server. "
            "Install requirements first."
        ) from _FASTMCP_IMPORT_ERROR

    resolved_settings = settings or Settings.from_env()
    service = create_intelligence_service(resolved_settings)

    try:
        seeded_rows = service.initialize(resolved_settings.seed_study_csv_path)
        logger.info("Initialized staging study table with %d row(s).", seeded_rows)
    except Exception as exc:  # pragma: no cover - runtime resilience path
        logger.warning("Staging initialization skipped: %s", exc)

    adapter = MCPToolAdapter(service)
    mcp = FastMCP(name="BioNexus Intelligence MCP")

    @mcp.tool(
        name="get_drug_leads",
        description="Return ranked drug lead hypotheses for a gene symbol or UniProt accession.",
    )
    def get_drug_leads(gene: str) -> str:
        return adapter.get_drug_leads(gene)

    @mcp.tool(
        name="explain_pathway",
        description="Explain likely pathway implications for a given GEO study accession.",
    )
    def explain_pathway(study_id: str) -> str:
        return adapter.explain_pathway(study_id)

    return mcp


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    server = create_mcp_server(settings)
    server.run(
        transport=settings.mcp_transport,
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
