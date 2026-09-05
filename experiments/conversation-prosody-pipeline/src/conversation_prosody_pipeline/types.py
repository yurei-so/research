"""Typed data structures for per-turn prosody observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TurnFeatures:
    """Measurable speech features for one conversational turn.

    Values are intentionally descriptive rather than interpretive. Upstream adapters
    may derive these from audio, transcript timing, or speech-recognition metadata.
    """

    duration_ms: float | None = None
    speech_rate_wpm: float | None = None
    pause_before_ms: float | None = None
    energy_rms: float | None = None
    pitch_variability_hz: float | None = None
    hesitation_count: int | None = None
    interruption_count: int | None = None

    def as_observations(self) -> dict[str, float]:
        """Return numeric fields that can participate in baseline comparisons."""

        observations: dict[str, float] = {}
        for key, value in asdict(self).items():
            if value is not None:
                observations[key] = float(value)
        return observations


@dataclass(frozen=True)
class ProsodyDeltas:
    """Per-feature movement relative to a conversation-local baseline."""

    absolute: dict[str, float]
    relative: dict[str, float]

    def to_dict(self) -> dict[str, dict[str, float]]:
        return {
            "absolute": self.absolute,
            "relative": self.relative,
        }


@dataclass(frozen=True)
class TurnTiming:
    """Transcript turn timing in milliseconds."""

    start_ms: float
    end_ms: float
    duration_ms: float

    def to_dict(self) -> dict[str, float]:
        return {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class RawTurn:
    """Generic upstream input for one conversational turn.

    This intentionally avoids audio buffers and speech-engine-specific objects. Adapters
    should translate external formats into this pipeline-native shape.
    """

    transcript: str
    timing: TurnTiming | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TurnMetadata:
    """Structured metadata passed downstream alongside a transcript turn."""

    transcript: str
    features: TurnFeatures
    deltas: ProsodyDeltas
    baseline_sample_count: int
    schema_version: str = "1.0"
    timing: TurnTiming | None = None

    def to_dict(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "schema_version": self.schema_version,
            "transcript": self.transcript,
            "features": self.features.as_observations(),
            "deltas": self.deltas.to_dict(),
            "baseline_sample_count": self.baseline_sample_count,
        }
        if self.timing is not None:
            metadata["timing"] = self.timing.to_dict()
        return metadata
