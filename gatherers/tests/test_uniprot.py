from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from uniprot import UniProtGatherer


@pytest.mark.asyncio
async def test_uniprot_gatherer_fetches_and_persists_partitioned_payload(tmp_path: Path) -> None:
    gatherer = UniProtGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"results": [{"primaryAccession": "P38398"}]}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        payload = await gatherer.fetch("BRCA1", organism="liver")

    assert payload["results"][0]["primaryAccession"] == "P38398"
    stored = next(tmp_path.rglob("BRCA1.json"))
    assert stored.exists()


@pytest.mark.asyncio
async def test_uniprot_gatherer_sanitizes_file_name(tmp_path: Path) -> None:
    gatherer = UniProtGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"results": []}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        await gatherer.fetch("BRCA1/../bad")

    stored = next(tmp_path.rglob("BRCA1_.._bad.json"))
    assert stored.exists()
