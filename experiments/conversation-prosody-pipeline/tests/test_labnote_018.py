import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_018"
SPEC = importlib.util.spec_from_file_location("run_two_speaker_ab", EXPERIMENT / "run_two_speaker_ab.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(MODULE)
REVIEW_SPEC = importlib.util.spec_from_file_location("prepare_review", EXPERIMENT / "prepare_review.py")
REVIEW = importlib.util.module_from_spec(REVIEW_SPEC); assert REVIEW_SPEC.loader; REVIEW_SPEC.loader.exec_module(REVIEW)


class TwoSpeakerConversationTest(unittest.TestCase):
    def test_frozen_protocol_is_balanced_and_valid(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        MODULE.validate_protocol(protocol)
        self.assertEqual(protocol["arms"], ["isolated", "conversation-aware"])
        self.assertEqual(len(protocol["scene"]["turns"]) * len(protocol["arms"]), 12)

    def test_two_distinct_voices_alternate(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        turns = protocol["scene"]["turns"]
        self.assertEqual(len(set(protocol["speakers"].values())), 2)
        self.assertEqual([turn["speaker"] for turn in turns], ["rowan", "mira"] * 3)

    def test_rejects_speech_editing_or_excessive_gap(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        protocol["post_processing"] = "time stretching"
        with self.assertRaisesRegex(ValueError, "may not be edited"):
            MODULE.validate_protocol(protocol)
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        protocol["scene"]["turns"][0]["gap_after_ms"] = 1500
        with self.assertRaisesRegex(ValueError, "turn gaps"):
            MODULE.validate_protocol(protocol)

    def test_review_page_hides_arm_identity(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"; run.mkdir()
            (run / "conversations").mkdir()
            for arm in ("isolated", "conversation-aware"):
                (run / "conversations" / f"{arm}.wav").write_bytes(arm.encode())
            report = {
                "format": "conversation-prosody.two-speaker-context-ab-run",
                "protocol_sha256": "1" * 64,
                "integrity_gate_passed": True,
                "conversations": [
                    {"arm": arm, "audio_path": f"conversations/{arm}.wav"}
                    for arm in ("isolated", "conversation-aware")],
            }
            (run / "report.json").write_text(json.dumps(report))
            review = root / "review"
            key = REVIEW.prepare(run, review)
            page = (review / "index.html").read_text()
            self.assertEqual(set(key.values()), {"isolated", "conversation-aware"})
            self.assertNotIn("conversation-aware.wav", page)
            self.assertNotIn("isolated.wav", page)


if __name__ == "__main__":
    unittest.main()
