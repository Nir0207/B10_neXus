from __future__ import annotations

import os


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_api_gateway_url() -> str:
    return os.getenv("BIONEXUS_API_URL", "http://localhost:8000")


def get_intelligence_api_url() -> str:
    return os.getenv("INTELLIGENCE_API_URL", "http://bionexus-intelligence-mcp:8080")
