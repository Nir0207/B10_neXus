from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_LAKE_ROOT = Path(__file__).resolve().parents[1] / "Lake" / "data_lake" / "raw"


def safe_path_component(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip()).strip("._")
    return safe or "unknown"


@dataclass(slots=True)
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0
    request_timeout_seconds: float = 20.0
    retry_attempts: int = 2
    retry_backoff_seconds: float = 0.5


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a gatherer is temporarily blocked after repeated failures."""


class BaseGatherer:
    def __init__(
        self,
        *,
        source_name: str,
        base_dir: str | Path | None = None,
        circuit_breaker: CircuitBreakerConfig | None = None,
    ) -> None:
        self.source_name = safe_path_component(source_name)
        self.base_dir = (
            Path(base_dir)
            if base_dir is not None
            else DEFAULT_LAKE_ROOT / self.source_name
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.circuit_breaker = circuit_breaker or CircuitBreakerConfig()
        self._consecutive_failures = 0
        self._circuit_opened_at: datetime | None = None

    async def request_json(
        self,
        *,
        method: str,
        url: str,
        request_name: str,
        expected_record_count: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = await self._request(
            method=method,
            url=url,
            request_name=request_name,
            **kwargs,
        )
        payload = response.json()
        record_count = expected_record_count
        if record_count is None:
            if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                record_count = len(payload["results"])
            elif isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                record_count = len(payload["data"])
        logger.info(
            "%s request succeeded with %s for %s%s",
            self.source_name,
            response.status_code,
            request_name,
            f" (records={record_count})" if record_count is not None else "",
        )
        return payload

    async def _request(
        self,
        *,
        method: str,
        url: str,
        request_name: str,
        **kwargs: Any,
    ) -> httpx.Response:
        self._ensure_circuit_closed()
        timeout = httpx.Timeout(self.circuit_breaker.request_timeout_seconds)
        last_error: Exception | None = None

        for attempt in range(1, self.circuit_breaker.retry_attempts + 2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(method=method, url=url, **kwargs)
                response.raise_for_status()
                self._reset_circuit()
                return response
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                should_retry = self._should_retry(exc=exc, attempt=attempt)
                logger.warning(
                    "%s request failed for %s on attempt %d/%d: %s",
                    self.source_name,
                    request_name,
                    attempt,
                    self.circuit_breaker.retry_attempts + 1,
                    exc,
                )
                if not should_retry:
                    self._record_failure(exc)
                    raise
                await asyncio.sleep(self.circuit_breaker.retry_backoff_seconds * attempt)

        self._record_failure(last_error)
        raise RuntimeError(f"Unexpected retry exhaustion for {request_name}") from last_error

    def save_json(
        self,
        *,
        stem: str,
        organ: str,
        payload: dict[str, Any] | list[Any],
    ) -> Path:
        destination_dir = self._resolve_partition_dir(organ=organ)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{safe_path_component(stem)}.json"
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Persisted %s payload to %s", self.source_name, destination)
        return destination

    def _resolve_partition_dir(self, *, organ: str) -> Path:
        date_partition = datetime.now(timezone.utc).date().isoformat()
        organ_partition = safe_path_component(organ or "systemic")
        return self.base_dir / f"date={date_partition}" / f"organ={organ_partition}"

    def _ensure_circuit_closed(self) -> None:
        if self._circuit_opened_at is None:
            return
        opened_for = datetime.now(timezone.utc) - self._circuit_opened_at
        if opened_for < timedelta(seconds=self.circuit_breaker.recovery_timeout_seconds):
            raise CircuitBreakerOpenError(
                f"{self.source_name} circuit breaker open for {opened_for.total_seconds():.1f}s"
            )
        self._circuit_opened_at = None
        self._consecutive_failures = 0

    def _reset_circuit(self) -> None:
        self._consecutive_failures = 0
        self._circuit_opened_at = None

    def _record_failure(self, exc: Exception | None) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.circuit_breaker.failure_threshold:
            self._circuit_opened_at = datetime.now(timezone.utc)
            logger.error(
                "%s circuit breaker opened after %d consecutive failures: %s",
                self.source_name,
                self._consecutive_failures,
                exc,
            )

    def _should_retry(self, *, exc: Exception, attempt: int) -> bool:
        if attempt > self.circuit_breaker.retry_attempts:
            return False
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            return status_code >= 500 or status_code == 429
        return True
