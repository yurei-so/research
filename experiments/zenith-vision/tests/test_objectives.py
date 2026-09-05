from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import OcrFailure, OcrScan, OcrToken, interpret_objectives_crop, objective_text_to_vision, save_objective_observation


class FakeOcr:
    def __init__(self, scan: OcrScan) -> None:
        self.result = scan

    def scan(self, image: Image.Image) -> OcrScan:
        return self.result


class ObjectiveInterpreterTests(unittest.TestCase):
    def test_emits_provenanced_objective_text(self) -> None:
        observation = interpret_objectives_crop(
            Image.new("RGB", (300, 500)),
            FakeOcr(OcrScan((OcrToken("Complete", 0.96), OcrToken("the", 0.93),
                             OcrToken("event", 0.91)), "fake", True)),
            captured_at="2026-08-25T00:00:00+00:00", source_crop_sha256="a" * 64,
        )
        self.assertEqual(observation.text, "Complete the event")
        self.assertEqual(observation.confidence, 0.91)
        self.assertTrue(observation.complete)
        self.assertEqual(observation.disclosure_policy, "operator-approved-objectives-text-v1")

    def test_fails_closed_on_ambiguous_or_identifier_text(self) -> None:
        for tokens in (
            (OcrToken("unclear", 0.4),),
            (OcrToken("Account.1234", 0.99),),
            (OcrToken("user@example.com", 0.99),),
        ):
            with self.subTest(tokens=tokens):
                with self.assertRaises(OcrFailure):
                    interpret_objectives_crop(
                        Image.new("RGB", (10, 10)), FakeOcr(OcrScan(tokens, "fake", True)),
                        captured_at="2026-08-25T00:00:00+00:00", source_crop_sha256="b" * 64,
                    )

    def test_marks_filtered_low_confidence_tokens_as_partial(self) -> None:
        observation = interpret_objectives_crop(
            Image.new("RGB", (10, 10)), FakeOcr(OcrScan((
                OcrToken("Complete", 0.9), OcrToken("the", 0.8),
                OcrToken("event", 0.95), OcrToken("noise", 0.1),
            ), "fake", True)), captured_at="2026-08-25T00:00:00+00:00",
            source_crop_sha256="d" * 64,
        )
        self.assertEqual(observation.text, "Complete the event")
        self.assertFalse(observation.complete)
        self.assertEqual(observation.rejected_token_count, 1)
        self.assertEqual(observation.retained_fraction, 0.75)

    def test_saves_owner_only_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            observation = interpret_objectives_crop(
                Image.new("RGB", (10, 10)), FakeOcr(OcrScan((
                    OcrToken("Complete", 1.0), OcrToken("the", 1.0), OcrToken("event", 1.0),
                ), "fake", True)),
                captured_at="2026-08-25T00:00:00+00:00", source_crop_sha256="c" * 64,
            )
            path = save_objective_observation(observation, Path(directory) / "private/observation.json")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text())["text"], "Complete the event")

    def test_adapts_to_provenance_carrying_visual_observation(self) -> None:
        objective = interpret_objectives_crop(
            Image.new("RGB", (10, 10)), FakeOcr(OcrScan((
                OcrToken("Complete", 0.9), OcrToken("the", 0.9), OcrToken("event", 0.9),
            ), "fake", True)), captured_at="2026-08-25T00:00:00+00:00",
            source_crop_sha256="e" * 64,
        )
        visual = objective_text_to_vision(objective)
        self.assertEqual(visual.kind, "objective_text")
        self.assertEqual(visual.evidence["source_crop_sha256"], "e" * 64)  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
