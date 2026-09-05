from __future__ import annotations

import json

from conversation_prosody_pipeline import MockFeatureExtractor, ProsodyPipeline, RawTurn


turn = RawTurn(
    transcript="Yeah... I'm fine.",
    metadata={"source": "demo"},
)

extractor = MockFeatureExtractor()
features = extractor.extract(turn)

pipeline = ProsodyPipeline()
metadata = pipeline.process_turn(
    transcript=turn.transcript,
    features=features,
    timing=turn.timing,
)

print(json.dumps(metadata.to_dict(), indent=2))
