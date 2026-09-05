import unittest

from conversation_prosody_pipeline import (
    FeatureExtractor,
    MockFeatureExtractor,
    ProsodyPipeline,
    RawTurn,
    TimingExtractor,
    TurnFeatures,
    TurnTiming,
)


class StaticTimingExtractor:
    def extract(self, turn: RawTurn) -> TurnTiming:
        return TurnTiming(start_ms=0.0, end_ms=1000.0, duration_ms=1000.0)


class ProsodyPipelineTests(unittest.TestCase):
    def test_first_turn_has_no_deltas_before_baseline_exists(self) -> None:
        pipeline = ProsodyPipeline()

        metadata = pipeline.process_turn("Hello.", TurnFeatures(speech_rate_wpm=120))

        self.assertEqual(metadata.baseline_sample_count, 0)
        self.assertEqual(metadata.deltas.absolute, {})
        self.assertEqual(metadata.deltas.relative, {})

    def test_second_turn_reports_observational_deltas(self) -> None:
        pipeline = ProsodyPipeline()
        pipeline.process_turn(
            "First turn.",
            TurnFeatures(speech_rate_wpm=100, pause_before_ms=200),
        )

        metadata = pipeline.process_turn(
            "Second turn.",
            TurnFeatures(speech_rate_wpm=75, pause_before_ms=500),
        )

        self.assertEqual(metadata.baseline_sample_count, 1)
        self.assertEqual(metadata.deltas.absolute["speech_rate_wpm"], -25)
        self.assertEqual(metadata.deltas.relative["speech_rate_wpm"], -0.25)
        self.assertEqual(metadata.deltas.absolute["pause_before_ms"], 300)
        self.assertEqual(metadata.to_dict()["transcript"], "Second turn.")

    def test_metadata_serializes_schema_version(self) -> None:
        pipeline = ProsodyPipeline()

        metadata = pipeline.process_turn("Versioned turn.", TurnFeatures(speech_rate_wpm=120))

        serialized = metadata.to_dict()
        self.assertEqual(serialized["schema_version"], "1.0")
        self.assertNotIn("timing", serialized)

    def test_metadata_serializes_timing_when_provided(self) -> None:
        pipeline = ProsodyPipeline()

        metadata = pipeline.process_turn(
            "Timed turn.",
            TurnFeatures(speech_rate_wpm=90),
            timing=TurnTiming(start_ms=125.0, end_ms=2125.0, duration_ms=2000.0),
        )

        self.assertEqual(
            metadata.to_dict()["timing"],
            {
                "start_ms": 125.0,
                "end_ms": 2125.0,
                "duration_ms": 2000.0,
            },
        )

    def test_raw_turn_creation_keeps_generic_input(self) -> None:
        timing = TurnTiming(start_ms=10.0, end_ms=510.0, duration_ms=500.0)

        turn = RawTurn(
            transcript="A generic turn.",
            timing=timing,
            metadata={"engine": "example"},
        )

        self.assertEqual(turn.transcript, "A generic turn.")
        self.assertEqual(turn.timing, timing)
        self.assertEqual(turn.metadata["engine"], "example")

    def test_mock_feature_extractor_returns_fixed_features(self) -> None:
        features = TurnFeatures(speech_rate_wpm=88.0, pause_before_ms=150.0)
        extractor = MockFeatureExtractor(features=features)

        extracted = extractor.extract(RawTurn(transcript="Any transcript."))

        self.assertEqual(extracted, features)

    def test_extractors_are_protocol_compatible(self) -> None:
        feature_extractor = MockFeatureExtractor()
        timing_extractor = StaticTimingExtractor()

        self.assertIsInstance(feature_extractor, FeatureExtractor)
        self.assertIsInstance(timing_extractor, TimingExtractor)

    def test_pipeline_accepts_extracted_features(self) -> None:
        turn = RawTurn(
            transcript="Extracted turn.",
            timing=TurnTiming(start_ms=0.0, end_ms=1200.0, duration_ms=1200.0),
        )
        extractor = MockFeatureExtractor(features=TurnFeatures(speech_rate_wpm=110.0))
        pipeline = ProsodyPipeline()

        metadata = pipeline.process_turn(
            transcript=turn.transcript,
            features=extractor.extract(turn),
            timing=turn.timing,
        )

        self.assertEqual(metadata.transcript, "Extracted turn.")
        self.assertEqual(metadata.features.speech_rate_wpm, 110.0)
        self.assertEqual(metadata.to_dict()["timing"]["duration_ms"], 1200.0)


if __name__ == "__main__":
    unittest.main()
