import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import Trial, load_campaign


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_009"
SPEC = importlib.util.spec_from_file_location("labnote_009", EXPERIMENT / "run.py")
LABNOTE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(LABNOTE)


class ReadinessSpanCompositionTest(unittest.TestCase):
    def setUp(self):
        corpus = json.loads((EXPERIMENT / "corpus.json").read_text())
        self.cases = {case["id"]: case for case in corpus["cases"]}

    def test_frozen_campaign_has_eight_matched_triplets(self):
        spec = load_campaign(EXPERIMENT / "manifest.json")
        self.assertEqual(len(spec.trials), 24)
        self.assertEqual({trial.parameters["arm"] for trial in spec.trials}, set(LABNOTE.ARMS))
        self.assertEqual(len({trial.parameters["case_id"] for trial in spec.trials}), 8)

    def test_readiness_contract_requires_ordered_bounded_span_and_suffix_evidence(self):
        value = {
            "draft_with_span": "[[DEFER_1:CLAIM]]The cache is lost.[[/DEFER_1]] The checkpoint remains valid and rebuilds the cache. [[READY_1]] Service is healthy.",
            "span_type": "CLAIM", "ready_when": ["checkpoint validity is established"],
        }
        draft, span, ready_when, visible = LABNOTE.validate_readiness(value)
        self.assertIn("The cache is lost.", span)
        self.assertNotIn(LABNOTE.READY, visible)
        self.assertEqual(ready_when, ["checkpoint validity is established"])
        self.assertIn(LABNOTE.READY, draft)
        with self.assertRaises(ValueError):
            LABNOTE.validate_readiness({**value,
                "draft_with_span": "[[READY_1]] [[DEFER_1:CLAIM]]x[[/DEFER_1]] enough right context follows here"})

    def test_readiness_span_replaces_whole_span_and_removes_protocol_markers(self):
        calls = []
        def generated(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                text = json.dumps({
                    "draft_with_span": "[[DEFER_1:CLAIM]]The cache and checkpoint were lost.[[/DEFER_1]] The durable checkpoint remained valid and rebuilt only the cache. [[READY_1]] The service recovered.",
                    "span_type": "CLAIM", "ready_when": ["checkpoint validity is known"],
                })
            else:
                text = json.dumps({"replacement": "Only the disposable cache was discarded."})
            return {"text": text, "thinking": "", "eval_count": 10,
                    "prompt_eval_count": 20, "elapsed_seconds": 0.1}
        with patch.object(LABNOTE, "generate", side_effect=generated):
            result = LABNOTE.execute_trial(Trial("trial", {
                "arm": "readiness-span", "case_id": "cache-recovery"}, 0),
                cases=self.cases, model="qwen3:8b", base_url="local")
        self.assertEqual(len(calls), 2)
        self.assertIn("Only the disposable cache was discarded.", result["final_text"])
        self.assertNotIn("DEFER", result["final_text"])
        self.assertNotIn("READY", result["final_text"])

    def test_review_keeps_known_negative_and_strong_control_separate(self):
        spec = load_campaign(EXPERIMENT / "manifest.json"); records = {}
        for trial in spec.trials:
            case_id = str(trial.parameters["case_id"]); arm = str(trial.parameters["arm"])
            records[trial.id] = {"status": "completed", "metrics": {},
                "private_result": {"arm": arm, "final_text": f"{case_id} {arm}"}}
        with tempfile.TemporaryDirectory() as temporary:
            intake = LABNOTE.write_review(state_directory=Path(temporary),
                campaign_digest=spec.digest, cases=self.cases, records=records, trials=spec.trials)
            self.assertTrue(intake["gate_passed"])
            self.assertEqual(intake["human_review_pair_count"], 16)
            self.assertEqual(set(intake["sessions"]), {
                "hole-only-vs-readiness-span", "full-revision-vs-readiness-span"})
            for name in intake["sessions"]:
                bundle = json.loads((Path(temporary) / f"review-{name}-bundle.json").read_text())
                key = json.loads((Path(temporary) / f"review-{name}-key.json").read_text())
                self.assertEqual(bundle["version"], 3)
                self.assertEqual(len(bundle["pairs"]), 8)
                self.assertEqual(key["treatment_arm"], "readiness_span")


if __name__ == "__main__": unittest.main()
