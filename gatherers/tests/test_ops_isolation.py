from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Any

from ops.openobserve_client import OpenObserveClient


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpxClient:
    def __init__(self, payload: dict[str, Any], **_: Any) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeHttpxClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def post(self, *_: Any, **__: Any) -> _FakeResponse:
        return _FakeResponse(self._payload)


def test_mock_gatherer_error_is_queryable_via_openobserve_api(monkeypatch) -> None:
    ops_logger = importlib.reload(importlib.import_module("ops.ops_logger"))
    captured_records: list[dict[str, Any]] = []

    class _RecordingSink:
        def __init__(self, **_: Any) -> None:
            return None

        def enqueue(self, message: Any) -> None:
            record = message.record
            captured_records.append(
                {
                    "message": str(record["message"]),
                    "gene_context": record["extra"].get("gene_context"),
                    "service_name": record["extra"].get("service_name"),
                }
            )

        def shutdown(self) -> None:
            return None

    monkeypatch.setattr(ops_logger, "_AsyncOTelSink", _RecordingSink)
    ops_logger.configure_logging(service_name="gatherers-test")

    stdlib_logger = logging.getLogger("gatherers.test")
    try:
        with ops_logger.gene_context("P12345"):
            raise RuntimeError("mock gatherer failure")
    except RuntimeError:
        with ops_logger.gene_context("P12345"):
            stdlib_logger.exception("Mock gatherer failure")

    assert captured_records
    assert captured_records[0]["gene_context"] == "P12345"
    assert captured_records[0]["service_name"] == "gatherers-test"

    query_payload = {
        "hits": [
            {
                "body": captured_records[0]["message"],
                "gene_context": captured_records[0]["gene_context"],
                "service_name": captured_records[0]["service_name"],
            }
        ]
    }
    monkeypatch.setattr(
        "ops.openobserve_client.httpx.Client",
        lambda **kwargs: _FakeHttpxClient(query_payload, **kwargs),
    )

    client = OpenObserveClient()
    result = client.query_logs("SELECT * FROM \"bionexus_app\" LIMIT 1", size=1)

    assert result["hits"][0]["body"] == "Mock gatherer failure"
    assert result["hits"][0]["gene_context"] == "P12345"


def test_gatherer_completes_when_ops_stack_is_down(monkeypatch) -> None:
    ops_logger = importlib.reload(importlib.import_module("ops.ops_logger"))

    class _BrokenSink:
        def __init__(self, **_: Any) -> None:
            raise ConnectionError("collector unavailable")

    monkeypatch.setattr(ops_logger, "_AsyncOTelSink", _BrokenSink)
    ops_logger.configure_logging(service_name="gatherers-test-down")
    stdlib_logger = logging.getLogger("gatherers.test.down")

    async def _mock_gatherer_task() -> str:
        try:
            raise RuntimeError("upstream error")
        except RuntimeError:
            stdlib_logger.exception("Handled gatherer error")
        return "completed"

    assert asyncio.run(_mock_gatherer_task()) == "completed"


def test_stdlib_logging_preserves_custom_extra_fields(monkeypatch) -> None:
    ops_logger = importlib.reload(importlib.import_module("ops.ops_logger"))
    captured_records: list[dict[str, Any]] = []

    class _RecordingSink:
        def __init__(self, **_: Any) -> None:
            return None

        def enqueue(self, message: Any) -> None:
            captured_records.append(dict(message.record["extra"]))

        def shutdown(self) -> None:
            return None

    monkeypatch.setattr(ops_logger, "_AsyncOTelSink", _RecordingSink)
    ops_logger.configure_logging(service_name="extra-test")

    logging.getLogger("extra.test").info("rum event", extra={"rum_session_id": "session-42", "rum_metric_name": "page_load"})

    assert captured_records
    assert captured_records[0]["rum_session_id"] == "session-42"
    assert captured_records[0]["rum_metric_name"] == "page_load"
