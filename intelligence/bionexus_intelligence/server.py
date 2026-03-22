from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.openobserve_client import OpenObserveClient, OpenObserveSettings
from ops.ops_logger import configure_logging

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

configure_logging(service_name="intelligence")
logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Thin adapter to keep FastMCP wiring separate from business logic."""

    def __init__(
        self,
        service: IntelligenceService,
        *,
        openobserve_client: OpenObserveClient | None = None,
    ) -> None:
        self._service = service
        self._openobserve_client = openobserve_client or OpenObserveClient()

    def get_drug_leads(self, gene: str) -> str:
        return self._service.get_drug_leads(gene)

    def explain_pathway(self, study_id: str) -> str:
        return self._service.explain_pathway(study_id)

    def render_visual_report(self, prompt: str, disease: str = "") -> str:
        report = self._service.render_visual_report(prompt=prompt, disease=disease or prompt)
        if report is None:
            return json.dumps({"error": "Disease trend snapshot not found"})
        return json.dumps(
            {
                "chart_type": report.chart_type,
                "title": report.title,
                "disease_id": report.disease_id,
                "disease_name": report.disease_name,
                "x_key": report.x_key,
                "y_key": report.y_key,
                "datasets": report.datasets,
                "clinical_summary": report.clinical_summary,
                "sources": [
                    "Source: Postgres disease_intelligence",
                    "Source: NCBI GEO",
                    "Source: UniProt",
                    "Source: Open Targets",
                    "Source: ChEMBL",
                ],
            }
        )

    def query_ops_logs(self, query_string: str) -> str:
        result = self._openobserve_client.query_logs(query_string=query_string)
        return json.dumps(result)


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

    adapter = MCPToolAdapter(
        service,
        openobserve_client=OpenObserveClient(
            OpenObserveSettings(
                base_url=resolved_settings.openobserve_base_url,
                organization=resolved_settings.openobserve_organization,
                username=resolved_settings.openobserve_username,
                password=resolved_settings.openobserve_password,
                log_stream=resolved_settings.openobserve_log_stream,
                timeout_seconds=10.0,
            )
        ),
    )
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

    @mcp.tool(
        name="render_visual_report",
        description="Return a JSON chart payload for disease trend and target analytics.",
    )
    def render_visual_report(prompt: str, disease: str = "") -> str:
        return adapter.render_visual_report(prompt, disease)

    @mcp.tool(
        name="query_ops_logs",
        description="Run a SQL-like query against recent OpenObserve log data for incident debugging.",
    )
    def query_ops_logs(query_string: str) -> str:
        return adapter.query_ops_logs(query_string)

    return mcp


def main() -> None:
    settings = Settings.from_env()
    server = create_mcp_server(settings)
    server.run(
        transport=settings.mcp_transport,
        host=settings.mcp_host,
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    main()
