from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import BoundingBox, DatasetManifest, admit_review_batch, admit_review_candidate, approve_annotation_batch, approve_annotation_proposal, create_annotation_proposal, save_batch_manifest, save_review_candidate


class AnnotationProposalTests(unittest.TestCase):
    def test_creates_private_visible_hud_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "item.png"
            Image.new("RGB", (1280, 720), "navy").save(media)
            overlay, proposal = create_annotation_proposal(media, root / "review", item_id="operator-00001")
            raw = json.loads(proposal.read_text())
            self.assertEqual([item["kind"] for item in raw["labels"]],
                             ["objectives", "skill_bar", "minimap"])
            self.assertEqual(raw["status"], "pending_human_review")
            self.assertEqual(stat.S_IMODE(overlay.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(proposal.stat().st_mode), 0o600)

    def test_accepts_item_specific_tight_boxes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = root / "item.png"
            Image.new("RGB", (100, 100), "navy").save(media)
            boxes = {
                "objectives": BoundingBox(0.8, 0.0, 0.2, 0.3),
                "skill_bar": BoundingBox(0.3, 0.8, 0.4, 0.2),
                "minimap": BoundingBox(0.8, 0.7, 0.2, 0.3),
            }
            _, proposal = create_annotation_proposal(media, root / "review", item_id="item", boxes=boxes)
            raw = json.loads(proposal.read_text())
            self.assertEqual(raw["method"], "item_specific_seed")
            self.assertEqual(raw["labels"][0]["box"], [0.8, 0.0, 0.2, 0.3])

    def test_approves_labels_into_manifest_and_admission_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, receipt, _ = save_review_candidate(
                Image.new("RGB", (100, 100), "navy"), root / "review",
                source_title="Synthetic", source_instance="fixture", source_class="fixture",
                ocr_token_count=0, mask_policy="operator-trusted-gameplay-v1",
            )
            dataset = root / "dataset"
            admit_review_candidate(candidate, receipt, dataset, item_id="item")
            _, proposal = create_annotation_proposal(candidate, dataset / "annotation-review", item_id="item")
            labels = approve_annotation_proposal(dataset, proposal, item_id="item")
            self.assertTrue(labels.is_file())
            self.assertEqual(json.loads(proposal.read_text())["status"], "approved")
            self.assertTrue(json.loads((dataset / "admissions/item.json").read_text())["labels_verified"])
            self.assertIsNotNone(DatasetManifest.load(dataset / "manifest.json").items[0].labels_path)

    def test_approves_complete_annotation_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = root / "batch"
            batch.mkdir()
            entries = []
            candidates = []
            for sequence, color in enumerate(("navy", "teal"), start=1):
                candidate, receipt, saved = save_review_candidate(
                    Image.new("RGB", (100, 100), color), batch,
                    source_title="Synthetic", source_instance="fixture", source_class="fixture",
                    ocr_token_count=0, mask_policy="operator-trusted-gameplay-v1",
                )
                entries.append({"sequence": sequence, "candidate": candidate.name,
                                "receipt": receipt.name, "candidate_sha256": saved.candidate_sha256})
                candidates.append(candidate)
            save_batch_manifest(batch, entries, started_at="2026-08-25T00:00:00+00:00")
            dataset = root / "dataset"
            admit_review_batch(batch, dataset)
            for item in DatasetManifest.load(dataset / "manifest.json").items:
                create_annotation_proposal(Path(item.media_path), dataset / "annotation-review", item_id=item.item_id)
            labels = approve_annotation_batch(dataset, dataset / "annotation-review")
            self.assertEqual(len(labels), 2)
            self.assertTrue(all(item.labels_path for item in DatasetManifest.load(dataset / "manifest.json").items))


if __name__ == "__main__":
    unittest.main()
