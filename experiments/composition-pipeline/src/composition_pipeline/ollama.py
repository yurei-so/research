"""Small standard-library Ollama client for bounded experiments."""

from __future__ import annotations

import json
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    pass


def generate(
    *,
    base_url: str,
    model: str,
    prompt: str,
    output_format: dict[str, Any] | None = None,
    temperature: float = 0,
    seed: int = 20260822,
    num_predict: int = 768,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_predict": num_predict,
        },
    }
    if output_format is not None:
        payload["format"] = output_format

    request = Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    started = monotonic()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            value = json.loads(response.read())
    except HTTPError as error:
        raise OllamaError(f"ollama_http_{error.code}") from error
    except URLError as error:
        raise OllamaError("ollama_unavailable") from error
    except (json.JSONDecodeError, TimeoutError) as error:
        raise OllamaError("ollama_invalid_response") from error

    text = value.get("response")
    if not isinstance(text, str):
        raise OllamaError("ollama_missing_response")
    return {
        "text": text,
        "eval_count": value.get("eval_count"),
        "prompt_eval_count": value.get("prompt_eval_count"),
        "elapsed_seconds": round(monotonic() - started, 6),
    }
