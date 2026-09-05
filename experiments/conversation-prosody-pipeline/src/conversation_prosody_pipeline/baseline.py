"""Conversation-local prosody baseline tracking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from conversation_prosody_pipeline.types import ProsodyDeltas, TurnFeatures


@dataclass
class ProsodyBaseline:
    """Running mean baseline for measurable turn features.

    The baseline is intentionally scoped to the active conversation. It is not a
    speaker profile and should not be persisted as biometric identity data.
    """

    totals: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    turn_count: int = 0

    @property
    def sample_count(self) -> int:
        return self.turn_count

    def mean(self, feature_name: str) -> float | None:
        count = self.counts.get(feature_name, 0)
        if count == 0:
            return None
        return self.totals[feature_name] / count

    def compare(self, features: TurnFeatures) -> ProsodyDeltas:
        absolute: dict[str, float] = {}
        relative: dict[str, float] = {}

        for name, value in features.as_observations().items():
            baseline = self.mean(name)
            if baseline is None:
                continue

            absolute[name] = value - baseline
            if baseline != 0:
                relative[name] = (value - baseline) / abs(baseline)

        return ProsodyDeltas(absolute=absolute, relative=relative)

    def update(self, features: TurnFeatures) -> None:
        for name, value in features.as_observations().items():
            self.totals[name] += value
            self.counts[name] += 1
        self.turn_count += 1
