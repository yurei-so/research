"""Loopback web server for the Prosody Demo."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import conversation_prosody_pipeline as cpp

from prosody_demo.ollama import OllamaClient, OllamaError
from prosody_demo.speech import SpeechError, SpeechProcessor

MAX_REQUEST_BYTES = 128 * 1024
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_MESSAGES = 100
MAX_MESSAGE_CHARS = 16_000
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
SYSTEM_PROMPT = (
    "You are taking part in a conversational voice-interface demo. "
    "Respond naturally and concisely. Acoustic measurements, when later supplied, "
    "are observations and must not be treated as proof of emotion, intent, identity, or health."
)


def _validate_chat(payload: Any) -> tuple[str, str, list[dict[str, str]]]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    model = payload.get("model")
    mode = payload.get("mode")
    messages = payload.get("messages")
    if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
        raise ValueError("Select a valid Ollama model")
    if mode not in {"baseline", "prosody"}:
        raise ValueError("Mode must be baseline or prosody")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError(f"Messages must contain 1 to {MAX_MESSAGES} entries")

    validated = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
            raise ValueError("Each message needs a user or assistant role")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_CHARS:
            raise ValueError(f"Message content must be 1 to {MAX_MESSAGE_CHARS} characters")
        validated.append({"role": message["role"], "content": content.strip()})
    prosody = payload.get("prosody")
    if mode == "prosody" and prosody is not None:
        if not isinstance(prosody, dict):
            raise ValueError("Prosody metadata must be a JSON object")
        serialized = json.dumps(prosody, sort_keys=True)
        if len(serialized) > 16_000:
            raise ValueError("Prosody metadata is too large")
        validated[-1]["content"] += (
            "\n\nMeasured delivery metadata for this turn (observations only):\n" + serialized
        )
    return model, mode, validated


class DemoHandler(SimpleHTTPRequestHandler):
    server_version = "ProsodyDemo/0.1"

    @property
    def ollama(self) -> OllamaClient:
        return self.server.ollama  # type: ignore[attr-defined]

    @property
    def speech(self) -> SpeechProcessor:
        return self.server.speech  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {"ok": True, "prosody_package": cpp.__name__, "modes": ["baseline", "prosody"]},
            )
            return
        if self.path == "/api/models":
            try:
                self._json(HTTPStatus.OK, {"models": self.ollama.list_models()})
            except OllamaError as error:
                self._json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/transcribe":
            self._transcribe(parse_qs(parsed.query))
            return
        if parsed.path == "/api/session/reset":
            self._reset_session()
            return
        if parsed.path != "/api/chat":
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            model, mode, messages = _validate_chat(self._read_json())
            started = time.perf_counter()
            result = self.ollama.chat(model, messages)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            message = result.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str):
                raise OllamaError("Ollama response did not contain assistant text")
            total_duration = result.get("total_duration", 0)
            ollama_ms = round(total_duration / 1_000_000, 1) if isinstance(total_duration, int) else 0
            self._json(
                HTTPStatus.OK,
                {
                    "message": {"role": "assistant", "content": content},
                    "mode": mode,
                    "timing": {"round_trip_ms": elapsed_ms, "ollama_total_ms": ollama_ms},
                },
            )
        except ValueError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except OllamaError as error:
            self._json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})

    def _transcribe(self, query: dict[str, list[str]]) -> None:
        session_id = query.get("session_id", [""])[0]
        if not SESSION_PATTERN.fullmatch(session_id):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "A valid session_id is required"})
            return
        try:
            audio = self._read_body(MAX_AUDIO_BYTES)
            result = self.speech.process(
                audio, self.headers.get("Content-Type", ""), session_id
            )
            self._json(HTTPStatus.OK, result)
        except (ValueError, SpeechError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _reset_session(self) -> None:
        try:
            payload = self._read_json()
            session_id = payload.get("session_id") if isinstance(payload, dict) else None
            if not isinstance(session_id, str) or not SESSION_PATTERN.fullmatch(session_id):
                raise ValueError("A valid session_id is required")
            self.speech.reset(session_id)
            self._json(HTTPStatus.OK, {"ok": True})
        except ValueError as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def _read_json(self) -> Any:
        body = self._read_body(MAX_REQUEST_BYTES)
        try:
            return json.loads(body)
        except json.JSONDecodeError as error:
            raise ValueError("Request body must be valid JSON") from error

    def _read_body(self, maximum: int) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if length <= 0 or length > maximum:
            raise ValueError(f"Request body must be 1 to {maximum} bytes")
        return self.rfile.read(length)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def create_server(
    host: str,
    port: int,
    ollama: OllamaClient | None = None,
    speech: SpeechProcessor | None = None,
) -> ThreadingHTTPServer:
    static_dir = Path(str(files("prosody_demo").joinpath("static")))
    handler = lambda *args, **kwargs: DemoHandler(  # noqa: E731
        *args, directory=str(static_dir), **kwargs
    )
    server = ThreadingHTTPServer((host, port), handler)
    server.ollama = ollama or OllamaClient(  # type: ignore[attr-defined]
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    )
    server.speech = speech or SpeechProcessor()  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Prosody Demo web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Prosody Demo listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
