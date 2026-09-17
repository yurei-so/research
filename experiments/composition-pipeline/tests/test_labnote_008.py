import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import Trial, load_campaign


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_008"
SPEC = importlib.util.spec_from_file_location("labnote_008", EXPERIMENT / "run.py")
LABNOTE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(LABNOTE)


class DeferredInfillCompositionTest(unittest.TestCase):
    def setUp(self):
        corpus = json.loads((EXPERIMENT / "corpus.json").read_text())
        self.cases = {case["id"]: case for case in corpus["cases"]}

    def test_frozen_campaign_has_eight_matched_triplets(self):
        spec = load_campaign(EXPERIMENT / "manifest.json")
        self.assertEqual(len(spec.trials), 24)
        self.assertEqual({trial.parameters["arm"] for trial in spec.trials}, set(LABNOTE.ARMS))
        self.assertEqual(len({trial.parameters["case_id"] for trial in spec.trials}), 8)

    def test_deferred_contract_requires_one_matching_hole_and_right_context(self):
        draft, token, reason = LABNOTE.validate_deferred({
            "draft_with_hole": "Approval covers [[DEFER_1:SCOPE]], and any changed definition requires a new review.",
            "hole_type": "SCOPE",
            "reason": "The exact boundary depends on the concluding instruction.",
        })
        self.assertEqual(token, "[[DEFER_1:SCOPE]]")
        self.assertIn(token, draft)
        self.assertTrue(reason)
        with self.assertRaises(ValueError):
            LABNOTE.validate_deferred({
                "draft_with_hole": "Too late [[DEFER_1:SCOPE]].",
                "hole_type": "SCOPE", "reason": "x",
            })
        with self.assertRaises(ValueError):
            LABNOTE.validate_deferred({
                "draft_with_hole": "A [[DEFER_1:SCOPE]] long enough suffix follows here. [[DEFER_2:CAUSE]]",
                "hole_type": "SCOPE", "reason": "x",
            })

    def test_deferred_arm_uses_two_calls_and_runtime_literal_replacement(self):
        calls = []

        def generated(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                text = json.dumps({
                    "draft_with_hole": "Approval covers [[DEFER_1:SCOPE]], and changed definitions require another review.",
                    "hole_type": "SCOPE",
                    "reason": "Choose the exact scope after writing the consequence.",
                })
            else:
                text = json.dumps({"replacement": "only the reviewed definition and fixed budget"})
            return {"text": text, "thinking": "", "eval_count": 10,
                    "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with patch.object(LABNOTE, "generate", side_effect=generated):
            result = LABNOTE.execute_trial(
                Trial("trial", {"arm": "deferred-infill", "case_id": "approval-scope"}, 0),
                cases=self.cases, model="qwen3:8b", base_url="local")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["metrics"]["call_count"], 2)
        self.assertNotIn("DEFER", result["final_text"])
        self.assertIn("only the reviewed definition and fixed budget", result["final_text"])
        self.assertEqual(result["deferred_telemetry"]["hole_type"], "SCOPE")

    def test_full_revision_is_a_two_call_control(self):
        calls = []

        def generated(**kwargs):
            calls.append(kwargs)
            return {"text": "A valid final response.", "thinking": "", "eval_count": 10,
                    "prompt_eval_count": 20, "elapsed_seconds": 0.1}

        with patch.object(LABNOTE, "generate", side_effect=generated):
            result = LABNOTE.execute_trial(
                Trial("trial", {"arm": "full-revision", "case_id": "approval-scope"}, 0),
                cases=self.cases, model="qwen3:8b", base_url="local")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["metrics"]["call_count"], 2)

    def test_review_compares_deferred_against_both_controls(self):
        spec = load_campaign(EXPERIMENT / "manifest.json")
        records = {}
        for trial in spec.trials:
            case_id = str(trial.parameters["case_id"])
            arm = str(trial.parameters["arm"])
            records[trial.id] = {
                "status": "completed", "metrics": {},
                "private_result": {"arm": arm, "case_id": case_id,
                                   "final_text": f"{case_id} {arm}"},
            }
        with tempfile.TemporaryDirectory() as temporary:
            intake = LABNOTE.write_review(
                state_directory=Path(temporary), campaign_digest=spec.digest,
                cases=self.cases, records=records, trials=spec.trials)
            self.assertTrue(intake["gate_passed"])
            self.assertEqual(intake["human_review_pair_count"], 16)
            self.assertEqual(set(intake["sessions"]),
                             {"direct-vs-deferred", "full-revision-vs-deferred"})
            for session_name, expected_baseline in (
                    ("direct-vs-deferred", "direct"),
                    ("full-revision-vs-deferred", "full_revision")):
                bundle = json.loads((Path(temporary) / f"review-{session_name}-bundle.json").read_text())
                key = json.loads((Path(temporary) / f"review-{session_name}-key.json").read_text())
                self.assertEqual(bundle["version"], 3)
                self.assertEqual(len(bundle["pairs"]), 8)
                self.assertEqual(key["baseline_arm"], expected_baseline)
                self.assertEqual(key["treatment_arm"], "deferred_infill")
                self.assertNotIn("deferred_telemetry", json.dumps(bundle))


if __name__ == "__main__":
    unittest.main()
