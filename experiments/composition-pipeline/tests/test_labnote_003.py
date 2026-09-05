import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import load_campaign


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "experiments/labnote_003/run.py"
SPEC = importlib.util.spec_from_file_location("labnote_003_run", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote003Test(unittest.TestCase):
    def test_frozen_campaign_reuses_bounded_labnote_002_cases(self) -> None:
        spec = load_campaign(ROOT / "experiments/labnote_003/manifest.json")
        corpus = json.loads((ROOT / "experiments/labnote_003/corpus.json").read_text())
        prior = json.loads((ROOT / "experiments/labnote_002/corpus.json").read_text())
        self.assertEqual(spec.campaign_id, "labnote_003")
        self.assertEqual(len(spec.trials), 48)
        self.assertEqual(corpus["cases"], prior["cases"])

    def test_finalize_only_is_valid_and_private(self) -> None:
        calls = 0

        def generated(**kwargs):
            nonlocal calls
            calls += 1
            text = json.dumps({"operations": [{"op": "finalize"}]}) \
                if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(calls, 72)
            self.assertEqual(result["campaign"]["completed_trials"], 48)
            self.assertEqual(result["summary"]["optional_editor"]["protocol_success_rate"], 1)
            self.assertEqual(result["blinded_review"]["pair_count"], 24)
            self.assertNotIn("clean direct rewrite", json.dumps(result).lower())
            telemetry = json.loads((state / "treatment-telemetry.json").read_text())
            self.assertEqual(telemetry["finalized_unchanged"], 24)
            self.assertEqual(telemetry["voluntarily_edited"], 0)
            bundle = json.loads((state / "review-bundle.json").read_text())
            key = json.loads((state / "review-key.json").read_text())
            self.assertNotIn("optional_editor", json.dumps(bundle))
            self.assertNotIn('"operations":', json.dumps(bundle))
            self.assertNotIn("clean direct rewrite", json.dumps(key).lower())
            self.assertEqual((state / "treatment-telemetry.json").stat().st_mode & 0o777, 0o600)

    def test_voluntary_edit_is_recorded_privately(self) -> None:
        def generated(**kwargs):
            text = json.dumps({"operations": [
                {"op": "replace", "old": "clean", "new": "clear"}, {"op": "finalize"},
            ]}) if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE, "generate", side_effect=generated):
                LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            telemetry = json.loads((state / "treatment-telemetry.json").read_text())
            self.assertEqual(telemetry["voluntarily_edited"], 24)
            self.assertEqual(telemetry["revision_operation_types"], {"replace": 24})

    def test_invalid_optional_edit_falls_back_and_remains_reviewable(self) -> None:
        def generated(**kwargs):
            text = "not json" if kwargs.get("output_format") is not None else "A clean direct rewrite."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["summary"]["optional_editor"]["protocol_success_rate"], 0)
            self.assertEqual(result["blinded_review"]["pair_count"], 24)
            telemetry = json.loads((state / "treatment-telemetry.json").read_text())
            self.assertEqual(telemetry["transactional_fallback"], 24)


if __name__ == "__main__":
    unittest.main()
