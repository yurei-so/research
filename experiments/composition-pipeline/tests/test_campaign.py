import json
import math
from pathlib import Path
import tempfile
import unittest

from composition_pipeline.campaign import CampaignError, Trial, load_campaign, run_campaign


def manifest(directory: Path, *, limits=None) -> Path:
    path = directory / "manifest.json"
    path.write_text(json.dumps({
        "format": "composition-pipeline.campaign",
        "version": 1,
        "campaign_id": "test_campaign",
        "axes": {"arm": ["a", "b"], "seed": [1, 2]},
        "repetitions": 2,
        "limits": limits or {"max_trials": 8, "retry_count": 0},
    }))
    return path


class CampaignTest(unittest.TestCase):
    def test_expands_deterministically_and_hides_parameters_and_private_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = load_campaign(manifest(root))
            calls: list[Trial] = []

            def execute(trial: Trial):
                calls.append(trial)
                return {"metrics": {"score": 1.0}, "generated_text": "private"}

            result = run_campaign(spec, root / "state", execute)
            self.assertEqual(len(calls), 8)
            self.assertEqual(result["successful_trials"], 8)
            self.assertNotIn("private", json.dumps(result))
            self.assertNotIn("parameters", json.dumps(result))
            checkpoint = json.loads((root / "state/checkpoint.json").read_text())
            self.assertIn("private", json.dumps(checkpoint))
            self.assertEqual((root / "state").stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / "state/checkpoint.json").stat().st_mode & 0o777, 0o600)

    def test_resume_skips_content_addressed_completed_trials(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = load_campaign(manifest(root))
            first_calls = 0

            def first(_: Trial):
                nonlocal first_calls
                first_calls += 1
                return {"metrics": {"ok": True}}

            run_campaign(spec, root / "state", first)
            second_calls = 0

            def second(_: Trial):
                nonlocal second_calls
                second_calls += 1
                return {"metrics": {"ok": True}}

            result = run_campaign(spec, root / "state", second)
            self.assertEqual(first_calls, 8)
            self.assertEqual(second_calls, 0)
            self.assertEqual(result["completed_trials"], 8)

    def test_budget_rejects_oversized_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(CampaignError, "exceeding max_trials"):
                load_campaign(manifest(root, limits={"max_trials": 7}))

    def test_stop_rule_halts_after_first_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = load_campaign(manifest(root, limits={
                "max_trials": 8, "retry_count": 1, "max_failures": 0,
            }))
            calls = 0

            def fail(_: Trial):
                nonlocal calls
                calls += 1
                raise RuntimeError("sensitive failure details")

            result = run_campaign(spec, root / "state", fail)
            self.assertEqual(calls, 2)
            self.assertEqual(result["completed_trials"], 1)
            self.assertEqual(result["failed_trials"], 1)
            self.assertEqual(result["stopped_reason"], "max_failures_exceeded")
            self.assertNotIn("sensitive", json.dumps(result))

    def test_changed_manifest_cannot_reuse_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = manifest(root)
            spec = load_campaign(path)
            run_campaign(spec, root / "state", lambda _: {"metrics": {"ok": True}})
            document = json.loads(path.read_text())
            document["axes"]["arm"].append("c")
            document["limits"]["max_trials"] = 12
            path.write_text(json.dumps(document))
            with self.assertRaisesRegex(CampaignError, "does not match"):
                run_campaign(
                    load_campaign(path), root / "state",
                    lambda _: {"metrics": {"ok": True}},
                )

    def test_non_json_result_and_non_finite_metric_become_bounded_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = load_campaign(manifest(root, limits={
                "max_trials": 8, "retry_count": 0, "max_failures": 0,
            }))
            result = run_campaign(
                spec, root / "state",
                lambda _: {"metrics": {"score": math.inf}, "unsafe": object()},
            )
            self.assertEqual(result["failed_trials"], 1)
            self.assertEqual(result["stopped_reason"], "max_failures_exceeded")


if __name__ == "__main__":
    unittest.main()
