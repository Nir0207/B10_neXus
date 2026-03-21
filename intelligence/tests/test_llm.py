from __future__ import annotations

from typing import Any

import pytest

from bionexus_intelligence.llm import LLMGenerationError, OllamaClient


class _DummyResponse:
    def __init__(self, *, payload: dict[str, Any], should_raise: bool = False):
        self._payload = payload
        self._should_raise = should_raise

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise RuntimeError("HTTP error")

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyClient:
    def __init__(self, *, response: _DummyResponse):
        self._response = response
        self.last_url: str | None = None
        self.last_json: dict[str, Any] | None = None

    def __enter__(self) -> _DummyClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def post(self, url: str, json: dict[str, Any]) -> _DummyResponse:
        self.last_url = url
        self.last_json = json
        return self._response


def test_ollama_client_generate_success(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = _DummyClient(response=_DummyResponse(payload={"response": "ok output"}))

    def _factory(*args: Any, **kwargs: Any) -> _DummyClient:
        return dummy

    monkeypatch.setattr("bionexus_intelligence.llm.httpx.Client", _factory)

    client = OllamaClient(host="http://ollama:11434", model="qwen2.5:3b")
    text = client.generate(system_prompt="sys", user_prompt="user", temperature=0.1)

    assert text == "ok output"
    assert dummy.last_url == "http://ollama:11434/api/generate"
    assert dummy.last_json is not None
    assert dummy.last_json["model"] == "qwen2.5:3b"


def test_ollama_client_generate_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = _DummyClient(response=_DummyResponse(payload={"response": ""}))

    def _factory(*args: Any, **kwargs: Any) -> _DummyClient:
        return dummy

    monkeypatch.setattr("bionexus_intelligence.llm.httpx.Client", _factory)

    client = OllamaClient(host="http://ollama:11434", model="qwen2.5:3b")

    with pytest.raises(LLMGenerationError, match="empty response"):
        client.generate(system_prompt="sys", user_prompt="user")
