"""Small, bounded Ollama HTTP client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    """An Ollama request failed or returned an invalid response."""


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 120.0

    def list_models(self) -> list[str]:
        payload = self._request("api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaError("Ollama returned an invalid model list")
        return [
            name for item in models
            if isinstance(item, dict) and isinstance((name := item.get("name")), str)
        ]

    def chat(self, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        return self._request(
            "api/chat", {"model": model, "messages": messages, "stream": False}
        )

    def _request(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            urljoin(self.base_url.rstrip("/") + "/", path),
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if data is None else "POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except HTTPError as error:
            detail = error.read(512).decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama returned HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OllamaError(f"Could not reach Ollama: {error}") from error
        if not isinstance(payload, dict):
            raise OllamaError("Ollama returned a non-object response")
        return payload
