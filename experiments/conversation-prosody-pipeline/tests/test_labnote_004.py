import sys
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).parents[1] / "experiments" / "labnote_004"
sys.path.insert(0, str(EXPERIMENT_DIR))

from corpus import build_cases  # noqa: E402
from run_inference import semantic_ir_error, validate_ir  # noqa: E402
from prepare_listener_review import prepare  # noqa: E402


class Labnote004CorpusTests(unittest.TestCase):
    def test_corpus_has_balanced_pairs(self):
        cases = build_cases()
        self.assertEqual(len(cases), 132)
        pairs = {}
        for case in cases:
            pairs.setdefault(case["pair_id"], []).append(case)
        self.assertEqual(len(pairs), 66)
        self.assertTrue(all(len(readings) == 2 for readings in pairs.values()))
        self.assertTrue(all(readings[0]["target"] == readings[1]["target"] for readings in pairs.values()))

    def test_every_phenomenon_has_six_pairs(self):
        pair_phenomena = {}
        for case in build_cases():
            pair_phenomena[case["pair_id"]] = case["phenomenon"]
        counts = {}
        for phenomenon in pair_phenomena.values():
            counts[phenomenon] = counts.get(phenomenon, 0) + 1
        self.assertEqual(set(counts.values()), {6})
        self.assertEqual(len(counts), 11)

    def test_ir_validation_accepts_gold(self):
        for case in build_cases():
            self.assertEqual(validate_ir(case["gold_ir"], case["target"]), case["gold_ir"])

    def test_ir_validation_records_non_target_focus_as_an_outcome(self):
        value = validate_ir({
            "focus_span": "missing",
            "focus_strength": 2,
            "boundary": "final",
            "delivery": "corrective",
            "pace": "normal",
        }, "The target sentence.")
        self.assertIn("exact substring", semantic_ir_error(value, "The target sentence."))

    def test_listener_slice_is_stratified_private_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); run_dir = root / "run"; output = root / "review"
            run_dir.mkdir(); audio = run_dir / "audio"; audio.mkdir()
            cases = build_cases(); (run_dir / "corpus.json").write_text(json.dumps(cases))
            rows = []
            for case in cases:
                for voice in ("af_heart", "am_adam"):
                    for condition in ("gold", "swapped"):
                        value = f"RIFF:{case['case_id']}:{voice}:{condition}".encode()
                        path = audio / f"{case['case_id']}-{voice}-{condition}.wav"
                        path.write_bytes(value)
                        rows.append({"case_id": case["case_id"], "voice": voice,
                            "condition": condition, "audio_path": str(path.relative_to(run_dir)),
                            "audio_sha256": hashlib.sha256(value).hexdigest()})
            (run_dir / "results.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
            calibration = root / "calibration.wav"; calibration.write_bytes(b"RIFF:calibration")
            intake = prepare(run_dir, output, calibration)
            self.assertEqual(intake["selected_authored_pairs"], 11)
            self.assertEqual(intake["selected_readings"], 22)
            self.assertEqual(intake["unique_review_pairs"], 22)
            self.assertEqual(intake["duplicate_changed_trials"], 0)
            self.assertEqual(sum(intake["voice_counts"].values()), 11)
            bundle = json.loads((output / "review-bundle.json").read_text())
            key = json.loads((output / "review-key.json").read_text())
            self.assertEqual(bundle["version"], 2)
            self.assertEqual(len(bundle["pairs"]), 22)
            self.assertEqual(len(key["pairs"]), 22)
            self.assertNotIn("intended_delivery", json.dumps(bundle))
            self.assertEqual((output / "review-key.json").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
