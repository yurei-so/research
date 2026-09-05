"""Dependency-free WAV file ingestion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import wave

from conversation_prosody_pipeline.types import RawTurn, TurnFeatures, TurnTiming


@dataclass(frozen=True)
class WavInfo:
    """Basic metadata read from a local PCM WAV file."""

    sample_rate: int
    frame_count: int
    duration_ms: float
    sample_width: int
    channel_count: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "sample_rate": self.sample_rate,
            "frame_count": self.frame_count,
            "duration_ms": self.duration_ms,
            "sample_width": self.sample_width,
            "channel_count": self.channel_count,
        }


def read_wav_info(path: str | Path) -> WavInfo:
    """Read basic WAV metadata using only the Python standard library."""

    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        sample_width = wav_file.getsampwidth()
        channel_count = wav_file.getnchannels()

    duration_ms = _duration_ms(frame_count, sample_rate)
    return WavInfo(
        sample_rate=sample_rate,
        frame_count=frame_count,
        duration_ms=duration_ms,
        sample_width=sample_width,
        channel_count=channel_count,
    )


def ingest_wav_file(path: str | Path, transcript: str) -> tuple[RawTurn, TurnFeatures]:
    """Create pipeline-native turn data from a WAV file and caller-provided transcript.

    This helper performs no speech recognition, emotion inference, speaker
    identification, or biometric profiling. It reads local WAV metadata and computes
    only basic measurements from PCM samples.
    """

    wav_path = Path(path)
    info, energy_rms = _read_wav_info_and_energy(wav_path)
    timing = TurnTiming(
        start_ms=0.0,
        end_ms=info.duration_ms,
        duration_ms=info.duration_ms,
    )
    features = TurnFeatures(
        duration_ms=info.duration_ms,
        energy_rms=energy_rms,
        speech_rate_wpm=_speech_rate_wpm(transcript, info.duration_ms),
    )
    turn = RawTurn(
        transcript=transcript,
        timing=timing,
        metadata={
            "source": "wav_file",
            "path": str(wav_path),
            "wav": info.to_dict(),
        },
    )
    return turn, features


def _read_wav_info_and_energy(path: Path) -> tuple[WavInfo, float | None]:
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        sample_width = wav_file.getsampwidth()
        channel_count = wav_file.getnchannels()
        frames = wav_file.readframes(frame_count)

    info = WavInfo(
        sample_rate=sample_rate,
        frame_count=frame_count,
        duration_ms=_duration_ms(frame_count, sample_rate),
        sample_width=sample_width,
        channel_count=channel_count,
    )
    return info, _energy_rms(frames, sample_width)


def _duration_ms(frame_count: int, sample_rate: int) -> float:
    if sample_rate <= 0:
        return 0.0
    return frame_count / sample_rate * 1000.0


def _speech_rate_wpm(transcript: str, duration_ms: float) -> float | None:
    if duration_ms <= 0:
        return None
    word_count = len(re.findall(r"\b[\w']+\b", transcript))
    return word_count / (duration_ms / 60000.0)


def _energy_rms(frames: bytes, sample_width: int) -> float | None:
    if not frames or sample_width not in {1, 2, 3, 4}:
        return None

    total_squares, sample_count = _sample_squares(frames, sample_width)
    if sample_count == 0:
        return None

    return (total_squares / sample_count) ** 0.5


def _sample_squares(frames: bytes, sample_width: int) -> tuple[float, int]:
    if sample_width not in {1, 2, 3, 4}:
        return 0.0, 0

    sample_count = len(frames) // sample_width
    total_squares = 0.0
    max_amplitude = float(1 << (sample_width * 8 - 1))

    for offset in range(0, sample_count * sample_width, sample_width):
        sample = _pcm_sample_to_int(frames[offset : offset + sample_width], sample_width)
        normalized = sample / max_amplitude
        total_squares += normalized * normalized

    return total_squares, sample_count


def _pcm_sample_to_int(sample: bytes, sample_width: int) -> int:
    if sample_width == 1:
        return sample[0] - 128
    if sample_width == 3:
        sign_byte = b"\xff" if sample[2] & 0x80 else b"\x00"
        return int.from_bytes(sample + sign_byte, byteorder="little", signed=True)
    return int.from_bytes(sample, byteorder="little", signed=True)
