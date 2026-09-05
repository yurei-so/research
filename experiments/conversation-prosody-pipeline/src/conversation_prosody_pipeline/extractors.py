"""Extractor interfaces for adapting upstream turn data into pipeline features."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from conversation_prosody_pipeline.types import RawTurn, TurnFeatures, TurnTiming


@runtime_checkable
class FeatureExtractor(Protocol):
    """Extract measurable turn features from generic upstream input."""

    def extract(self, turn: RawTurn) -> TurnFeatures: ...


@runtime_checkable
class TimingExtractor(Protocol):
    """Extract turn timing from generic upstream input."""

    def extract(self, turn: RawTurn) -> TurnTiming: ...


@dataclass(frozen=True)
class MockFeatureExtractor:
    """Dependency-free feature extractor for examples and tests."""

    features: TurnFeatures = field(
        default_factory=lambda: TurnFeatures(
            speech_rate_wpm=120.0,
            pause_before_ms=250.0,
            energy_rms=0.5,
            pitch_variability_hz=30.0,
            hesitation_count=0,
            interruption_count=0,
        )
    )

    def extract(self, turn: RawTurn) -> TurnFeatures:
        return self.features
