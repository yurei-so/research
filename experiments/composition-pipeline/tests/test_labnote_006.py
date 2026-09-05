import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composition_pipeline.campaign import load_campaign

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("labnote_006_run", ROOT / "experiments/labnote_006/run.py")
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote006Test(unittest.TestCase):
    def test_frozen_campaign_is_bounded_and_diverse(self) -> None:
        spec = load_campaign(ROOT / "experiments/labnote_006/manifest.json")
        self.assertEqual(len(spec.trials), 120)
        self.assertEqual(len({trial.parameters["case_id"] for trial in spec.trials}), 12)
        self.assertEqual(spec.retry_count, 4)

    def test_none_diagnosis_skips_repair_and_review(self) -> None:
        calls = 0
        def generated(**kwargs):
            nonlocal calls
            calls += 1
            text = "Good baseline."
            if kwargs.get("output_format") == LABNOTE.DIAGNOSIS_SCHEMA:
                text = json.dumps({"defect": "none", "evidence": "", "repair_instruction": ""})
            return {"text": text, "eval_count": 3, "prompt_eval_count": 4, "elapsed_seconds": 0.01}
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(LABNOTE, "generate", side_effect=generated), \
                patch.object(LABNOTE.BASE, "generate", side_effect=generated):
            result = LABNOTE.run_labnote(state_directory=Path(temporary), model="test", base_url="local")
        self.assertEqual(calls, 240)
        self.assertFalse(result["review"]["gate_passed"])
        self.assertEqual(result["review"]["human_review_pair_count"], 0)

    def test_gate_requires_unique_pairs_and_case_coverage(self) -> None:
        corpus = json.loads((ROOT / "experiments/labnote_006/corpus.json").read_text())
        cases = {case["id"]: case for case in corpus["cases"]}
        spec = load_campaign(ROOT / "experiments/labnote_006/manifest.json")
        records = {}
        for index, trial in enumerate(spec.trials[:24]):
            records[trial.id] = {"status": "completed", "metrics": {"verified_repair": True},
                "private_result": {"case_id": trial.parameters["case_id"],
                    "baseline": f"baseline {index}", "repaired": f"repair {index}"}}
        with tempfile.TemporaryDirectory() as temporary:
            result = LABNOTE.write_review_intake(state_directory=Path(temporary),
                campaign_digest=spec.digest, cases=cases, records=records, trials=spec.trials)
            bundle = json.loads((Path(temporary) / "review-bundle.json").read_text())
        self.assertTrue(result["gate_passed"])
        self.assertGreaterEqual(result["eligible_case_count"], 6)
        self.assertEqual(len(bundle["pairs"]), 24)

    def test_targeted_repair_uses_one_exact_whole_buffer_replacement(self) -> None:
        trial = load_campaign(ROOT / "experiments/labnote_006/manifest.json").trials[0]
        cases = {str(trial.parameters["case_id"]): {"task": "Make it clear.", "draft": "Bad."}}
        def generated(**kwargs):
            if kwargs.get("output_format") == LABNOTE.DIAGNOSIS_SCHEMA:
                text = json.dumps({"defect": "tone_mismatch", "evidence": "Bad.",
                                   "repair_instruction": "Use a calm tone."})
            elif kwargs.get("output_format") == LABNOTE.VERIFY_SCHEMA:
                text = json.dumps({"defect_fixed": True, "material_regression": False})
            elif "Repair exactly one diagnosed defect" in kwargs.get("prompt", ""):
                text = "Clear and calm."
            else:
                text = "Bad."
            return {"text": text, "eval_count": 3, "prompt_eval_count": 4, "elapsed_seconds": 0.01}
        with patch.object(LABNOTE, "generate", side_effect=generated), \
                patch.object(LABNOTE.BASE, "generate", side_effect=generated):
            result = LABNOTE.execute_trial(trial, cases=cases, model="test", base_url="local")
        self.assertEqual(result["repaired"], "Clear and calm.")
        self.assertTrue(result["metrics"]["verified_repair"])


if __name__ == "__main__":
    unittest.main()
