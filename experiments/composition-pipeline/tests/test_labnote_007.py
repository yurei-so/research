import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import Trial, load_campaign


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_007"
SPEC = importlib.util.spec_from_file_location("labnote_007", EXPERIMENT / "run.py")
LABNOTE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(LABNOTE)


class DeepThinkingCompositionTest(unittest.TestCase):
    def test_frozen_campaign_has_twelve_matched_pairs(self):
        spec = load_campaign(EXPERIMENT / "manifest.json")
        self.assertEqual(len(spec.trials), 24)
        self.assertEqual({trial.parameters["arm"] for trial in spec.trials}, set(LABNOTE.ARMS))
        self.assertEqual(len({trial.parameters["case_id"] for trial in spec.trials}), 12)

    def test_only_thinking_control_changes_between_matched_calls(self):
        corpus = json.loads((EXPERIMENT / "corpus.json").read_text())
        cases = {case["id"]: case for case in corpus["cases"]}
        calls = []

        def generated(**kwargs):
            calls.append(kwargs)
            return {"text": "A valid revision.",
                    "thinking": "careful analysis" if kwargs["think"] else "",
                    "eval_count": 20, "prompt_eval_count": 30, "elapsed_seconds": 0.2}

        with patch.object(LABNOTE, "generate", side_effect=generated):
            for arm in LABNOTE.ARMS:
                LABNOTE.execute_trial(Trial(arm, {"arm": arm, "case_id": "lease-priority"}, 0),
                                      cases=cases, model="qwen3:8b", base_url="local")
        left = {key: value for key, value in calls[0].items() if key != "think"}
        right = {key: value for key, value in calls[1].items() if key != "think"}
        self.assertEqual(left, right)
        self.assertEqual([call["think"] for call in calls], [False, True])

    def test_review_gate_requires_eight_changed_pairs_and_hides_thinking(self):
        spec = load_campaign(EXPERIMENT / "manifest.json")
        corpus = json.loads((EXPERIMENT / "corpus.json").read_text())
        cases = {case["id"]: case for case in corpus["cases"]}
        records = {}
        for trial in spec.trials:
            case_id = str(trial.parameters["case_id"])
            arm = str(trial.parameters["arm"])
            changed = list(cases).index(case_id) < 8
            text = f"{case_id} candidate {'a' if arm == LABNOTE.ARMS[0] else 'b'}" if changed else case_id
            records[trial.id] = {"status": "completed", "metrics": {},
                                 "private_result": {"final_text": text, "thinking": "secret"}}
        with tempfile.TemporaryDirectory() as temporary:
            intake = LABNOTE.write_review(state_directory=Path(temporary),
                campaign_digest=spec.digest, cases=cases, records=records, trials=spec.trials)
            self.assertTrue(intake["gate_passed"])
            self.assertEqual(intake["human_review_pair_count"], 8)
            bundle = json.loads((Path(temporary) / "review-bundle.json").read_text())
            self.assertNotIn("secret", json.dumps(bundle))
            self.assertNotIn("thinking-enabled", json.dumps(bundle))
            key = json.loads((Path(temporary) / "review-key.json").read_text())
            self.assertEqual({item["candidate_a_arm"] for item in key["pairs"]}
                             | {item["candidate_b_arm"] for item in key["pairs"]},
                             {"direct_rewrite", "thinking_enabled"})


if __name__ == "__main__":
    unittest.main()
