from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


def _microseconds(dt: datetime) -> int:
    return int(dt.timestamp() * 1_000_000)


@dataclass(frozen=True, slots=True)
class OpenObserveSettings:
    base_url: str
    organization: str
    username: str
    password: str
    log_stream: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> OpenObserveSettings:
        return cls(
            base_url=os.getenv("OPENOBSERVE_BASE_URL", "http://localhost:5080").rstrip("/"),
            organization=os.getenv("OPENOBSERVE_ORG", "default"),
            username=os.getenv("OPENOBSERVE_USERNAME", "root@bionexus.local"),
            password=os.getenv("OPENOBSERVE_PASSWORD", "BioNexusOps123!"),
            log_stream=os.getenv("OPENOBSERVE_LOG_STREAM", "bionexus_app"),
            timeout_seconds=float(os.getenv("OPENOBSERVE_TIMEOUT_SECONDS", "10")),
        )

    def authorization_header(self) -> str:
        token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"


class OpenObserveClient:
    def __init__(self, settings: OpenObserveSettings | None = None) -> None:
        self.settings = settings or OpenObserveSettings.from_env()

    def query_logs(
        self,
        query_string: str,
        *,
        minutes_ago: int = 60,
        size: int = 50,
        stream_name: str | None = None,
    ) -> dict[str, Any]:
        stream = stream_name or self.settings.log_stream
        sql = self._normalize_query(query_string=query_string, stream_name=stream, size=size)
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(minutes=minutes_ago)

        payload: dict[str, Any] = {
            "query": {
                "sql": sql,
                "start_time": _microseconds(start_time),
                "end_time": _microseconds(end_time),
                "from": 0,
                "size": size,
            },
            "search_type": "ui",
            "timeout": 0,
        }
        headers = {
            "Authorization": self.settings.authorization_header(),
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            response = client.post(
                f"{self.settings.base_url}/api/{self.settings.organization}/_search",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _normalize_query(
        *,
        query_string: str,
        stream_name: str,
        size: int,
    ) -> str:
        normalized = query_string.strip()
        if not normalized:
            return f'SELECT * FROM "{stream_name}" ORDER BY _timestamp DESC LIMIT {size}'
        lowered = normalized.lower()
        if lowered.startswith("select "):
            return normalized.replace("{stream}", f'"{stream_name}"')
        escaped = normalized.replace("'", "''")
        return (
            f'SELECT * FROM "{stream_name}" '
            f"WHERE match_all('{escaped}') "
            f"ORDER BY _timestamp DESC LIMIT {size}"
        )
