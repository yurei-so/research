from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import save_review_candidate


class ReviewCandidateTests(unittest.TestCase):
    def test_saves_owner_only_candidate_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate, receipt_path, receipt = save_review_candidate(
                Image.new("RGB", (20, 10), "purple"), Path(directory) / "review",
                source_title="Synthetic", source_instance="fixture", source_class="fixture",
                ocr_token_count=3, mask_policy="fixture", now=datetime(2026, 8, 25, tzinfo=timezone.utc),
            )
            self.assertEqual(stat.S_IMODE(candidate.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(receipt_path.stat().st_mode), 0o600)
            self.assertFalse(receipt.dataset_admitted)
            raw = json.loads(receipt_path.read_text())
            self.assertEqual(raw["candidate_sha256"], receipt.candidate_sha256)
            self.assertNotIn("ocr_text", raw)

    def test_rejects_negative_token_count_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_review_candidate(Image.new("RGB", (1, 1)), Path(directory),
                                      source_title="x", source_instance="x", source_class="x",
                                      ocr_token_count=-1, mask_policy="fixture")


if __name__ == "__main__":
    unittest.main()
