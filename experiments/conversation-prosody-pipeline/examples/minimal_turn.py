from __future__ import annotations

import json

from conversation_prosody_pipeline import ProsodyPipeline, TurnFeatures


pipeline = ProsodyPipeline()

pipeline.process_turn(
    "Yeah, that's fine.",
    TurnFeatures(
        speech_rate_wpm=152,
        pause_before_ms=120,
        energy_rms=0.38,
        pitch_variability_hz=42,
        hesitation_count=0,
    ),
)

metadata = pipeline.process_turn(
    "Yeah... I'm fine.",
    TurnFeatures(
        speech_rate_wpm=98,
        pause_before_ms=860,
        energy_rms=0.21,
        pitch_variability_hz=24,
        hesitation_count=1,
    ),
)

print(json.dumps(metadata.to_dict(), indent=2))
