import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import load_campaign


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "experiments/labnote_004/run.py"
SPEC = importlib.util.spec_from_file_location("labnote_004_run", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote004Test(unittest.TestCase):
    def test_frozen_campaign_has_120_matched_pairs(self) -> None:
        spec = load_campaign(ROOT / "experiments/labnote_004/manifest.json")
        self.assertEqual(spec.campaign_id, "labnote_004")
        self.assertEqual(len(spec.trials), 240)

    def test_normalization_is_narrow_and_deterministic(self) -> None:
        self.assertEqual(LABNOTE.normalize_output(" a  \r\n b\t\n"), "a\n b")
        self.assertNotEqual(LABNOTE.normalize_output("Alpha"), LABNOTE.normalize_output("alpha"))

    def test_unchanged_outputs_become_automatic_ties(self) -> None:
        def generated(**kwargs):
            text = json.dumps({"operations": [{"op": "finalize"}]}) \
                if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["matched_pair_count"], 120)
            self.assertEqual(result["review"]["automatic_tie_count"], 120)
            self.assertEqual(result["review"]["human_review_pair_count"], 0)

    def test_only_changed_outputs_enter_blinded_review(self) -> None:
        def generated(**kwargs):
            text = json.dumps({"operations": [
                {"op": "replace", "old": "clean", "new": "clear"}, {"op": "finalize"},
            ]}) if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["automatic_tie_count"], 0)
            self.assertEqual(result["review"]["human_review_pair_count"], 120)
            bundle = json.loads((state / "review-bundle.json").read_text())
            key = json.loads((state / "review-key.json").read_text())
            self.assertEqual(len(bundle["pairs"]), 120)
            self.assertNotIn("optional_editor", json.dumps(bundle))
            self.assertNotIn("clean direct rewrite", json.dumps(key).lower())

    def test_independent_baseline_drift_does_not_create_review_pairs(self) -> None:
        base_calls = 0

        def generated(**kwargs):
            nonlocal base_calls
            if kwargs.get("output_format") is not None:
                text = json.dumps({"operations": [{"op": "finalize"}]})
            else:
                base_calls += 1
                text = "First baseline." if base_calls <= 120 else "Drifted baseline."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["automatic_tie_count"], 120)
            self.assertEqual(result["review"]["human_review_pair_count"], 0)

    def test_invalid_editor_fallback_is_an_automatic_tie(self) -> None:
        def generated(**kwargs):
            text = "not json" if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["automatic_tie_count"], 120)
            self.assertEqual(result["review"]["human_review_pair_count"], 0)
            telemetry = json.loads((state / "treatment-telemetry.json").read_text())
            self.assertEqual(telemetry["transactional_fallback"], 120)


if __name__ == "__main__":
    unittest.main()
