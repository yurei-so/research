from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import DatasetManifest, ManifestError, admit_review_batch, admit_review_candidate, save_batch_manifest, save_review_candidate


class AdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.candidate, self.receipt, _ = save_review_candidate(
            Image.new("RGB", (20, 10), "green"), root / "review",
            source_title="Synthetic", source_instance="fixture", source_class="fixture",
            ocr_token_count=1, mask_policy="operator-trusted-gameplay-v1",
            now=datetime(2026, 8, 25, tzinfo=timezone.utc),
        )
        self.dataset = root / "dataset"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_admits_digest_bound_private_holdout_without_labels(self) -> None:
        manifest_path = admit_review_candidate(
            self.candidate, self.receipt, self.dataset, item_id="operator-00001",
            now=datetime(2026, 8, 25, 1, tzinfo=timezone.utc),
        )
        manifest = DatasetManifest.load(manifest_path)
        self.assertEqual(manifest.split_counts(), {"train": 0, "validation": 0, "test": 1})
        self.assertIsNone(manifest.items[0].labels_path)
        self.assertTrue(json.loads(self.receipt.read_text())["dataset_admitted"])
        admission = json.loads((self.dataset / "admissions/operator-00001.json").read_text())
        self.assertFalse(admission["labels_verified"])

    def test_changed_candidate_is_rejected(self) -> None:
        self.candidate.write_bytes(b"changed")
        with self.assertRaisesRegex(ManifestError, "digest mismatch"):
            admit_review_candidate(self.candidate, self.receipt, self.dataset, item_id="operator-00001")

    def test_wrong_policy_is_rejected(self) -> None:
        raw = json.loads(self.receipt.read_text())
        raw["mask_policy"] = "unknown"
        self.receipt.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ManifestError, "mask policy"):
            admit_review_candidate(self.candidate, self.receipt, self.dataset, item_id="operator-00001")

    def test_admits_review_batch_as_unlabeled_test_holdout(self) -> None:
        root = Path(self.temp.name)
        batch = root / "batch"
        batch.mkdir()
        entries = []
        for sequence, color in enumerate(("red", "blue"), start=1):
            candidate, receipt, saved = save_review_candidate(
                Image.new("RGB", (20, 10), color), batch,
                source_title="Synthetic", source_instance="fixture", source_class="fixture",
                ocr_token_count=0, mask_policy="operator-trusted-gameplay-v1",
            )
            entries.append({"sequence": sequence, "candidate": candidate.name, "receipt": receipt.name,
                            "candidate_sha256": saved.candidate_sha256})
        save_batch_manifest(
            batch, entries, started_at="2026-08-25T00:00:00+00:00", ui_scale="normal",
        )
        manifest_path = admit_review_batch(
            batch, root / "holdout", dataset_name="operator-normal-holdout-v1", ui_scale="normal",
        )
        manifest = DatasetManifest.load(manifest_path)
        self.assertEqual(len(manifest.items), 2)
        self.assertTrue(all(item.labels_path is None and item.split == "test" for item in manifest.items))
        batch_raw = json.loads((batch / "batch.json").read_text())
        self.assertEqual(batch_raw["status"], "approved")
        self.assertEqual(batch_raw["dataset_name"], "operator-normal-holdout-v1")
        self.assertEqual(batch_raw["ui_scale"], "normal")
        self.assertEqual(json.loads(manifest_path.read_text())["ui_scale"], "normal")


if __name__ == "__main__":
    unittest.main()
