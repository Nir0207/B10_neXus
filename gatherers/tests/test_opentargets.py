from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opentargets import OpenTargetsGatherer


@pytest.mark.asyncio
async def test_opentargets_gatherer_fetches_and_persists_payload(tmp_path: Path) -> None:
    gatherer = OpenTargetsGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"data": {"disease": {"id": "EFO_0000572"}}}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        payload = await gatherer.fetch_liver_evidence("EFO_0000572")

    assert payload["data"]["disease"]["id"] == "EFO_0000572"
    assert next(tmp_path.rglob("EFO_0000572_evidence.json")).exists()


@pytest.mark.asyncio
async def test_opentargets_gatherer_raises_on_graphql_errors(tmp_path: Path) -> None:
    gatherer = OpenTargetsGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"errors": [{"message": "Rate limit exceeded"}]}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        with pytest.raises(RuntimeError, match="GraphQL error"):
            await gatherer.fetch_liver_evidence("EFO_0000572")
