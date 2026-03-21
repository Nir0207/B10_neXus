from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration for the Intelligence service."""

    pg_dsn: str
    ollama_host: str
    ollama_model: str
    ollama_timeout_seconds: float
    mcp_host: str
    mcp_port: int
    mcp_transport: str
    rag_snippet_limit: int
    pathway_limit: int
    opentargets_evidence_path: Path
    seed_study_csv_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            pg_dsn=os.getenv(
                "PG_DSN",
                "postgresql://bionexus_user:bionexus_dev_password@localhost:5432/bionexus",
            ),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            ollama_timeout_seconds=_env_float("OLLAMA_TIMEOUT_SECONDS", 90.0),
            mcp_host=os.getenv("MCP_HOST", "0.0.0.0"),
            mcp_port=_env_int("MCP_PORT", 8080),
            mcp_transport=os.getenv("MCP_TRANSPORT", "sse"),
            rag_snippet_limit=_env_int("RAG_SNIPPET_LIMIT", 5),
            pathway_limit=_env_int("PATHWAY_LIMIT", 5),
            opentargets_evidence_path=_resolve_path(
                os.getenv(
                    "OT_EVIDENCE_PATH",
                    str(_REPO_ROOT / "Lake" / "data_lake" / "raw" / "opentargets" / "EFO_0000572_evidence.json"),
                )
            ),
            seed_study_csv_path=_resolve_path(
                os.getenv(
                    "STUDY_CSV_PATH",
                    str(_REPO_ROOT / "Lake" / "data_lake" / "silver" / "silver_ncbi_studies.csv"),
                )
            ),
        )


def _env_int(key: str, default: int) -> int:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    return int(raw_value)


def _env_float(key: str, default: float) -> float:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default
    return float(raw_value)


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (_REPO_ROOT / path).resolve()
