import json
import os
import tempfile
import unittest
from pathlib import Path

from narrative_steering.experiment import (
    ContractError,
    analyze_judgments,
    prepare_review,
    protocol_digest,
)


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_001"
PROTOCOL = EXPERIMENT / "frozen-protocol.json"
CORPUS = EXPERIMENT / "corpus.json"


class NarrativeSteeringExperimentTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(PROTOCOL.read_text())
        self.corpus = json.loads(CORPUS.read_text())

    def generations(self):
        records = []
        for model in ("model-a", "model-b", "model-c"):
            for case in self.corpus["cases"]:
                for variant in self.corpus["prompt_variants"]:
                    for sample in (1, 2):
                        records.append({
                            "model_id": model,
                            "case_id": case["id"],
                            "variant_id": variant["id"],
                            "sample_id": sample,
                            "text": f"The scene continues with a concrete beat numbered {sample}.",
                        })
        return {
            "format": "narrative-steering.generations",
            "version": 1,
            "protocol_digest": protocol_digest(self.protocol, self.corpus),
            "models": ["model-a", "model-b", "model-c"],
            "records": records,
        }

    def prepare(self, directory):
        generations_path = directory / "generations.json"
        bundle_path = directory / "review" / "bundle.json"
        reveal_path = directory / "review" / "reveal.json"
        generations_path.write_text(json.dumps(self.generations()))
        bundle, reveal = prepare_review(PROTOCOL, CORPUS, generations_path, bundle_path, reveal_path)
        return bundle, reveal, bundle_path, reveal_path

    def test_prepares_complete_blinded_owner_private_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle, reveal, bundle_path, reveal_path = self.prepare(Path(temp))
            self.assertEqual(48, len(bundle["items"]))
            self.assertEqual(48, len(reveal["items"]))
            self.assertNotIn("model-a", bundle_path.read_text())
            self.assertIn("model-a", reveal_path.read_text())
            self.assertTrue(all("model_id" not in item for item in bundle["items"]))
            self.assertEqual(0o600, os.stat(bundle_path).st_mode & 0o777)
            self.assertEqual(0o600, os.stat(reveal_path).st_mode & 0o777)
            self.assertEqual(0o700, os.stat(bundle_path.parent).st_mode & 0o777)

    def test_rejects_missing_cells_and_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            generations = self.generations()
            generations["records"].pop()
            generations_path = directory / "generations.json"
            generations_path.write_text(json.dumps(generations))
            with self.assertRaisesRegex(ContractError, "incomplete generation matrix"):
                prepare_review(PROTOCOL, CORPUS, generations_path, directory / "bundle.json", directory / "reveal.json")

            bundle, reveal, bundle_path, reveal_path = self.prepare(directory)
            self.assertEqual(48, len(bundle["items"]))
            with self.assertRaisesRegex(ContractError, "refusing to overwrite"):
                prepare_review(PROTOCOL, CORPUS, directory / "generations.json", bundle_path, reveal_path)

    def test_aggregates_raw_centered_and_prompt_shift_vectors(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            bundle, reveal, bundle_path, reveal_path = self.prepare(directory)
            score_by_model = {"model-a": 1, "model-b": 0, "model-c": -1}
            model_by_item = {item["item_id"]: item["model_id"] for item in reveal["items"]}
            judgments = {
                "format": "narrative-steering.judgments",
                "version": 1,
                "bundle_digest": bundle["bundle_digest"],
                "judgments": [
                    {
                        "item_id": item["item_id"],
                        "scores": {
                            dimension: score_by_model[model_by_item[item["item_id"]]]
                            + (1 if dimension == "agency" and item["variant_id"] == "agency_guard" else 0)
                            for dimension in self.protocol["dimensions"]
                        },
                        "confidence": 3,
                    }
                    for item in bundle["items"]
                ],
            }
            judgments_path = directory / "judgments.json"
            judgments_path.write_text(json.dumps(judgments))
            result = analyze_judgments(PROTOCOL, bundle_path, reveal_path, judgments_path)
            self.assertEqual(1.5, result["models"]["model-a"]["raw"]["agency"]["mean"])
            self.assertEqual(1.0, result["models"]["model-a"]["raw"]["closure"]["mean"])
            self.assertEqual(1.0, result["models"]["model-a"]["agency_guard_shift"]["agency"])
            self.assertAlmostEqual(1.0, result["models"]["model-a"]["matched_centered"]["closure"]["mean"])
            self.assertEqual(1.0, result["models"]["model-a"]["by_state_variant"]["late-train"]["neutral"]["closure"])
            self.assertEqual(3.0, result["models"]["model-a"]["mean_confidence"])

    def test_rejects_incomplete_score_vector(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            bundle, reveal, bundle_path, reveal_path = self.prepare(directory)
            judgments = {
                "format": "narrative-steering.judgments",
                "version": 1,
                "bundle_digest": bundle["bundle_digest"],
                "judgments": [
                    {"item_id": item["item_id"], "scores": {"agency": 0}, "confidence": 2}
                    for item in bundle["items"]
                ],
            }
            judgments_path = directory / "judgments.json"
            judgments_path.write_text(json.dumps(judgments))
            with self.assertRaisesRegex(ContractError, "incomplete score vector"):
                analyze_judgments(PROTOCOL, bundle_path, reveal_path, judgments_path)


if __name__ == "__main__":
    unittest.main()
