"""Experimental WAV-backed streaming ingestion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import wave

from conversation_prosody_pipeline.audio_file import (
    WavInfo,
    _duration_ms,
    _sample_squares,
    _speech_rate_wpm,
)
from conversation_prosody_pipeline.types import RawTurn, TurnFeatures, TurnTiming


@dataclass(frozen=True)
class AudioChunk:
    """A generic chunk of raw PCM audio plus stream timing."""

    raw_pcm: bytes
    sample_rate: int
    sample_width: int
    channel_count: int
    start_ms: float
    duration_ms: float
    is_final: bool


def iter_wav_chunks(
    path: str | Path,
    chunk_duration_ms: float = 100.0,
) -> Iterator[AudioChunk]:
    """Yield deterministic PCM chunks from a WAV file without loading it all at once."""

    if chunk_duration_ms <= 0:
        raise ValueError("chunk_duration_ms must be greater than zero")

    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channel_count = wav_file.getnchannels()
        frame_count = wav_file.getnframes()
        frames_per_chunk = max(1, round(sample_rate * chunk_duration_ms / 1000.0))
        frames_read = 0

        while frames_read < frame_count:
            remaining_frames = frame_count - frames_read
            frames_to_read = min(frames_per_chunk, remaining_frames)
            raw_pcm = wav_file.readframes(frames_to_read)
            frame_size = sample_width * channel_count
            actual_frames = len(raw_pcm) // frame_size if frame_size > 0 else 0
            if actual_frames == 0:
                break

            start_ms = _duration_ms(frames_read, sample_rate)
            frames_read += actual_frames
            yield AudioChunk(
                raw_pcm=raw_pcm,
                sample_rate=sample_rate,
                sample_width=sample_width,
                channel_count=channel_count,
                start_ms=start_ms,
                duration_ms=_duration_ms(actual_frames, sample_rate),
                is_final=frames_read >= frame_count,
            )


class StreamingFeatureAccumulator:
    """Accumulate minimal turn features from ordered audio chunks."""

    def __init__(self) -> None:
        self.sample_rate: int | None = None
        self.sample_width: int | None = None
        self.channel_count: int | None = None
        self.chunk_count = 0
        self.total_duration_ms = 0.0
        self.total_sample_count = 0
        self._total_squares = 0.0
        self._is_complete = False

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    def add_chunk(self, chunk: AudioChunk) -> None:
        """Accept one ordered chunk and update duration and RMS state."""

        if self._is_complete:
            raise ValueError("cannot add chunks after a final chunk")

        self._set_or_validate_format(chunk)
        total_squares, sample_count = _sample_squares(chunk.raw_pcm, chunk.sample_width)
        self._total_squares += total_squares
        self.total_sample_count += sample_count
        self.total_duration_ms += chunk.duration_ms
        self.chunk_count += 1
        if chunk.is_final:
            self._is_complete = True

    def finalize(self, transcript: str | None = None) -> TurnFeatures:
        """Return the currently accumulated features."""

        energy_rms = None
        if self.total_sample_count > 0:
            energy_rms = (self._total_squares / self.total_sample_count) ** 0.5

        return TurnFeatures(
            duration_ms=self.total_duration_ms,
            energy_rms=energy_rms,
            speech_rate_wpm=_speech_rate_wpm(transcript or "", self.total_duration_ms)
            if transcript is not None
            else None,
        )

    def wav_info(self) -> WavInfo | None:
        """Return stream audio metadata after at least one chunk has been seen."""

        if self.sample_rate is None or self.sample_width is None or self.channel_count is None:
            return None
        frame_count = self.total_sample_count // self.channel_count if self.channel_count else 0
        return WavInfo(
            sample_rate=self.sample_rate,
            frame_count=frame_count,
            duration_ms=self.total_duration_ms,
            sample_width=self.sample_width,
            channel_count=self.channel_count,
        )

    def _set_or_validate_format(self, chunk: AudioChunk) -> None:
        if self.sample_rate is None:
            self.sample_rate = chunk.sample_rate
            self.sample_width = chunk.sample_width
            self.channel_count = chunk.channel_count
            return

        if (
            chunk.sample_rate != self.sample_rate
            or chunk.sample_width != self.sample_width
            or chunk.channel_count != self.channel_count
        ):
            raise ValueError("audio chunk format changed during stream")


def ingest_wav_stream(
    path: str | Path,
    transcript: str,
    chunk_duration_ms: float = 100.0,
) -> tuple[RawTurn, TurnFeatures]:
    """Simulate stream ingestion from a WAV file and return pipeline-native data."""

    wav_path = Path(path)
    accumulator = StreamingFeatureAccumulator()
    for chunk in iter_wav_chunks(wav_path, chunk_duration_ms=chunk_duration_ms):
        accumulator.add_chunk(chunk)

    features = accumulator.finalize(transcript)
    timing = TurnTiming(
        start_ms=0.0,
        end_ms=features.duration_ms or 0.0,
        duration_ms=features.duration_ms or 0.0,
    )
    wav_info = accumulator.wav_info()
    turn = RawTurn(
        transcript=transcript,
        timing=timing,
        metadata={
            "source": "wav_stream",
            "path": str(wav_path),
            "chunk_duration_ms": chunk_duration_ms,
            "chunk_count": accumulator.chunk_count,
            "is_complete": accumulator.is_complete,
            "wav": wav_info.to_dict() if wav_info is not None else None,
        },
    )
    return turn, features
