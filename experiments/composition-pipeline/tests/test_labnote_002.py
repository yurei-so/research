import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import load_campaign


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "experiments/labnote_002/run.py"
SPEC = importlib.util.spec_from_file_location("labnote_002_run", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote002Test(unittest.TestCase):
    def test_frozen_campaign_has_expected_bounded_matrix(self) -> None:
        spec = load_campaign(ROOT / "experiments/labnote_002/manifest.json")
        corpus = json.loads((ROOT / "experiments/labnote_002/corpus.json").read_text())
        self.assertEqual(spec.campaign_id, "labnote_002")
        self.assertEqual(len(spec.trials), 48)
        self.assertEqual(len(corpus["cases"]), 6)

    def test_mocked_campaign_is_private_blinded_and_resumable(self) -> None:
        calls = 0

        def generated(**kwargs):
            nonlocal calls
            calls += 1
            text = (
                json.dumps({"operations": [
                    {"op": "append", "text": " Revised."},
                    {"op": "finalize"},
                ]})
                if kwargs.get("output_format") is not None
                else "A clean direct rewrite."
            )
            return {
                "text": text, "eval_count": 10, "prompt_eval_count": 20,
                "elapsed_seconds": 0.1,
            }

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(
                    state_directory=state, model="test", base_url="http://127.0.0.1",
                )
            self.assertEqual(calls, 48)
            self.assertEqual(result["campaign"]["completed_trials"], 48)
            self.assertEqual(result["campaign"]["failed_trials"], 0)
            self.assertEqual(result["blinded_review"]["pair_count"], 24)
            self.assertEqual(result["summary"]["schema_revision"]["protocol_success_rate"], 1)
            self.assertNotIn("clean direct rewrite", json.dumps(result).lower())
            bundle = json.loads((state / "review-bundle.json").read_text())
            key = json.loads((state / "review-key.json").read_text())
            self.assertEqual(len(bundle["pairs"]), 24)
            self.assertEqual(len(key["pairs"]), 24)
            self.assertNotIn("candidate_a_arm", json.dumps(bundle))
            self.assertNotIn("direct_rewrite", json.dumps(bundle))
            self.assertNotIn("clean direct rewrite", json.dumps(key).lower())
            self.assertEqual((state / "review-bundle.json").stat().st_mode & 0o777, 0o600)

            calls = 0
            with patch.object(LABNOTE, "generate", side_effect=generated):
                resumed = LABNOTE.run_labnote(
                    state_directory=state, model="test", base_url="http://127.0.0.1",
                )
            self.assertEqual(calls, 0)
            self.assertEqual(resumed["blinded_review"], result["blinded_review"])


if __name__ == "__main__":
    unittest.main()
