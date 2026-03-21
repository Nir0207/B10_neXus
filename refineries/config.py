"""
Centralised configuration for the BioNexus Refinery.

All paths are resolved relative to the repository root so the package
works regardless of the working directory the runner uses.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Repository layout ────────────────────────────────────────────────────────
# In Docker the data lake is mounted at /data_lake; locally it lives under
# the repository root.  Either env var or the default relative path is used.
_REPO_ROOT: Path = Path(__file__).resolve().parents[1]


def _existing_data_lake_root() -> Path:
    for candidate in (
        _REPO_ROOT / "Lake" / "data_lake",
        _REPO_ROOT / "lake" / "data_lake",
    ):
        if candidate.exists():
            return candidate
    return _REPO_ROOT / "Lake" / "data_lake"


_DATA_LAKE_ROOT: Path = _existing_data_lake_root()
_DEFAULT_RAW_ROOT: Path = _DATA_LAKE_ROOT / "raw"
_DEFAULT_SILVER: Path = _DATA_LAKE_ROOT / "silver"

RAW_ROOT_DIR: Path = Path(os.getenv("RAW_ROOT_DIR", str(_DEFAULT_RAW_ROOT)))
RAW_UNIPROT_DIR: Path = RAW_ROOT_DIR / "uniprot"
RAW_NCBI_DIR: Path = RAW_ROOT_DIR / "ncbi"

SILVER_CSV_DIR: Path = Path(os.getenv("SILVER_DIR", str(_DEFAULT_SILVER)))

# ── Idempotency manifest ─────────────────────────────────────────────────────
# In Docker the manifest is written inside the silver layer mount so it
# survives container restarts.
MANIFEST_PATH: Path = Path(
    os.getenv("MANIFEST_PATH", str(Path(__file__).resolve().parent / ".processed_manifest.json"))
)

# ── Database connections ─────────────────────────────────────────────────────
# Docker service names: postgres:5432, neo4j:7687  (Lake bionexus-network)
# Locally: localhost equivalents.
PG_DSN: str = os.getenv(
    "PG_DSN",
    "postgresql://bionexus_user:bionexus_dev_password@localhost:5432/bionexus",
)

NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "bionexus_dev_password")
