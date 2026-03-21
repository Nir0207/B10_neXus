from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ncbi import NCBIGatherer


@pytest.mark.asyncio
async def test_ncbi_gatherer_fetches_search_and_summary(tmp_path: Path) -> None:
    gatherer = NCBIGatherer(base_dir=tmp_path)
    search_response = Mock()
    search_response.json.return_value = {"esearchresult": {"idlist": ["123", "456"]}}
    search_response.raise_for_status.return_value = None

    summary_response = Mock()
    summary_response.json.return_value = {"result": {"uids": ["123"], "123": {"title": "Study"}}}
    summary_response.raise_for_status.return_value = None

    with patch(
        "httpx.AsyncClient.request",
        new_callable=AsyncMock,
        side_effect=[search_response, summary_response],
    ):
        payload = await gatherer.fetch_geo_studies("BRCA1", organ="liver")

    assert payload["result"]["123"]["title"] == "Study"
    assert next(tmp_path.rglob("BRCA1_studies.json")).exists()


@pytest.mark.asyncio
async def test_ncbi_gatherer_persists_empty_payload_when_no_records(tmp_path: Path) -> None:
    gatherer = NCBIGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"esearchresult": {"idlist": []}}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        payload = await gatherer.fetch_geo_studies("EMPTY")

    assert payload == []
    assert next(tmp_path.rglob("EMPTY_studies.json")).exists()
