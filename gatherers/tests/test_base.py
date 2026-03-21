from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from base import BaseGatherer, CircuitBreakerConfig, CircuitBreakerOpenError


class DummyGatherer(BaseGatherer):
    def __init__(self, base_dir: Path) -> None:
        super().__init__(
            source_name="dummy",
            base_dir=base_dir,
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout_seconds=60.0,
                retry_attempts=0,
            ),
        )


@pytest.mark.asyncio
async def test_base_gatherer_opens_circuit_after_threshold(tmp_path: Path) -> None:
    gatherer = DummyGatherer(tmp_path)

    request = httpx.Request("GET", "https://example.org")
    response = httpx.Response(status_code=503, request=request)
    error = httpx.HTTPStatusError("upstream unavailable", request=request, response=response)

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, side_effect=error):
        with pytest.raises(httpx.HTTPStatusError):
            await gatherer._request(method="GET", url="https://example.org", request_name="first")
        with pytest.raises(httpx.HTTPStatusError):
            await gatherer._request(method="GET", url="https://example.org", request_name="second")
        with pytest.raises(CircuitBreakerOpenError):
            await gatherer._request(method="GET", url="https://example.org", request_name="third")


def test_base_gatherer_persists_partitioned_json(tmp_path: Path) -> None:
    gatherer = DummyGatherer(tmp_path)
    target = gatherer.save_json(stem="BRCA1", organ="liver", payload={"results": []})

    assert target.exists()
    assert "date=" in str(target.parent)
    assert target.parent.name == "organ=liver"
