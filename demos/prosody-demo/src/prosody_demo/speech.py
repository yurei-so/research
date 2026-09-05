"""Local recorded-turn transcription and CPP metadata extraction."""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any

from conversation_prosody_pipeline import ProsodyPipeline, ingest_wav_stream


class SpeechError(RuntimeError):
    """A recorded turn could not be decoded or transcribed."""


class SpeechProcessor:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.environ.get("WHISPER_MODEL", "small.en")
        self._model: Any = None
        self._model_lock = threading.Lock()
        self._sessions: dict[str, ProsodyPipeline] = {}
        self._sessions_lock = threading.Lock()

    def process(self, audio: bytes, content_type: str, session_id: str) -> dict[str, Any]:
        suffix = self._suffix_for(content_type)
        with tempfile.TemporaryDirectory(prefix="prosody-demo-") as directory:
            source = Path(directory, f"recording{suffix}")
            wav = Path(directory, "turn.wav")
            source.write_bytes(audio)
            self._convert_to_wav(source, wav)
            transcript, language, confidence = self._transcribe(wav)
            if not transcript:
                raise SpeechError("No speech was detected in the recording")
            turn, features = ingest_wav_stream(wav, transcript, chunk_duration_ms=100)
            metadata = self._pipeline_for(session_id).process_turn(
                transcript, features, timing=turn.timing
            )
            return {
                "transcript": transcript,
                "language": language,
                "language_probability": confidence,
                "prosody": metadata.to_dict(),
            }

    def reset(self, session_id: str) -> None:
        with self._sessions_lock:
            self._sessions.pop(session_id, None)

    def _pipeline_for(self, session_id: str) -> ProsodyPipeline:
        with self._sessions_lock:
            return self._sessions.setdefault(session_id, ProsodyPipeline())

    def _transcribe(self, wav: Path) -> tuple[str, str | None, float | None]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise SpeechError(
                "Speech support is not installed; run pip install -e '.[speech]'"
            ) from error
        with self._model_lock:
            if self._model is None:
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            segments, info = self._model.transcribe(
                str(wav), language="en", beam_size=5, vad_filter=True
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
        probability = getattr(info, "language_probability", None)
        return transcript, getattr(info, "language", None), probability

    @staticmethod
    def _convert_to_wav(source: Path, target: Path) -> None:
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target),
                ],
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SpeechError(f"Could not run ffmpeg: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace")[-1000:]
            raise SpeechError(f"Could not decode the recording: {detail}")

    @staticmethod
    def _suffix_for(content_type: str) -> str:
        mime = content_type.split(";", 1)[0].strip().lower()
        suffixes = {
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
        }
        try:
            return suffixes[mime]
        except KeyError as error:
            raise SpeechError(f"Unsupported recording type: {mime or 'missing'}") from error
