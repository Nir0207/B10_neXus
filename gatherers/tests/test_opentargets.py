from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opentargets import OpenTargetsGatherer


@pytest.mark.asyncio
async def test_opentargets_gatherer_fetches_and_persists_payload(tmp_path: Path) -> None:
    gatherer = OpenTargetsGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"data": {"disease": {"id": "EFO_0000572", "associatedTargets": {"rows": []}}}}
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


@pytest.mark.asyncio
async def test_opentargets_gatherer_resolves_disease_by_search(tmp_path: Path) -> None:
    gatherer = OpenTargetsGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {
        "data": {
            "search": {
                "hits": [
                    {"id": "MONDO_0004975", "name": "Alzheimer disease", "entity": "disease"}
                ]
            }
        }
    }
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        disease_id, disease_name = await gatherer.resolve_disease_id("Alzheimer disease")

    assert disease_id == "MONDO_0004975"
    assert disease_name == "Alzheimer disease"


@pytest.mark.asyncio
async def test_opentargets_gatherer_raises_when_disease_payload_is_null(tmp_path: Path) -> None:
    gatherer = OpenTargetsGatherer(base_dir=tmp_path)
    response = Mock()
    response.json.return_value = {"data": {"disease": None}}
    response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        with pytest.raises(RuntimeError, match="payload was null"):
            await gatherer.fetch_disease_evidence("EFO_0000249", organ="brain")


def test_opentargets_gatherer_extracts_top_target_genes() -> None:
    payload = {
        "data": {
            "disease": {
                "associatedTargets": {
                    "rows": [
                        {"target": {"approvedSymbol": "PSEN1"}},
                        {"target": {"approvedSymbol": "APP"}},
                        {"target": {"approvedSymbol": "PSEN1"}},
                    ]
                }
            }
        }
    }

    assert OpenTargetsGatherer.extract_top_target_genes(payload, limit=2) == ["PSEN1", "APP"]
