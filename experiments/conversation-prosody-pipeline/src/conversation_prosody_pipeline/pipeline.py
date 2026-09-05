"""Minimal middleware pipeline for transcript turns and prosody features."""

from __future__ import annotations

from conversation_prosody_pipeline.baseline import ProsodyBaseline
from conversation_prosody_pipeline.types import TurnFeatures, TurnMetadata, TurnTiming


class ProsodyPipeline:
    """Build downstream metadata while maintaining conversation-local state."""

    def __init__(self, baseline: ProsodyBaseline | None = None) -> None:
        self.baseline = baseline or ProsodyBaseline()

    def process_turn(
        self,
        transcript: str,
        features: TurnFeatures,
        timing: TurnTiming | None = None,
    ) -> TurnMetadata:
        deltas = self.baseline.compare(features)
        metadata = TurnMetadata(
            transcript=transcript,
            features=features,
            deltas=deltas,
            baseline_sample_count=self.baseline.sample_count,
            timing=timing,
        )
        self.baseline.update(features)
        return metadata
