import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import load_campaign


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("labnote_005_run", ROOT / "experiments/labnote_005/run.py")
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote005Test(unittest.TestCase):
    def test_frozen_campaign_has_sampling_axis(self) -> None:
        spec = load_campaign(ROOT / "experiments/labnote_005/manifest.json")
        self.assertEqual(len(spec.trials), 240)
        self.assertEqual({trial.parameters["sampling_temperature"] for trial in spec.trials}, {0.35})

    def test_duplicate_changed_pairs_are_reviewed_once(self) -> None:
        def generated(**kwargs):
            text = json.dumps({"operations": [{"op": "append", "text": " Better."}, {"op": "finalize"}]}) \
                if kwargs.get("output_format") is not None else "Baseline."
            self.assertEqual(kwargs["temperature"], 0.35)
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["changed_trial_count"], 120)
            self.assertEqual(result["review"]["unique_review_pair_count"], 1)
            self.assertEqual(result["review"]["duplicate_changed_trial_count"], 119)
            self.assertEqual(result["review"]["duplicate_group_size_counts"], {120: 1})
            bundle = json.loads((state / "review-bundle.json").read_text())
            self.assertEqual(len(bundle["pairs"]), 1)

    def test_unique_changes_remain_unique_review_items(self) -> None:
        editor_calls = 0

        def generated(**kwargs):
            nonlocal editor_calls
            if kwargs.get("output_format") is not None:
                editor_calls += 1
                text = json.dumps({"operations": [
                    {"op": "append", "text": f" Change {editor_calls}."}, {"op": "finalize"},
                ]})
            else:
                text = "Baseline."
            return {"text": text, "eval_count": 10, "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state"
            with patch.object(LABNOTE.BASE, "generate", side_effect=generated):
                result = LABNOTE.run_labnote(state_directory=state, model="test", base_url="http://127.0.0.1")
            self.assertEqual(result["review"]["unique_review_pair_count"], 120)
            self.assertEqual(result["review"]["duplicate_changed_trial_count"], 0)


if __name__ == "__main__":
    unittest.main()
