from __future__ import annotations

from dataclasses import dataclass

import httpx


class LLMGenerationError(RuntimeError):
    """Raised when a local LLM generation request fails."""


@dataclass(frozen=True, slots=True)
class OllamaClient:
    host: str
    model: str
    timeout_seconds: float = 90.0

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMGenerationError(f"Ollama request failed: {exc}") from exc

        body = response.json()
        text = body.get("response")
        if not isinstance(text, str) or not text.strip():
            raise LLMGenerationError("Ollama returned an empty response body.")

        return text.strip()
