from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.model_bundle import (
    digest_panel_corpus, load_model_bundle, region_plan_digest, write_model_bundle,
)


class ModelBundleTests(unittest.TestCase):
    def test_corpus_digest_binds_labels_and_masked_tiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "batch"
            root.mkdir()
            (root / "labels.json").write_text(json.dumps({"items": [{"id": "sample-000", "panels": []}]}))
            for tile in ("left", "center"):
                Image.new("RGB", (20, 20), "navy").save(root / f"sample-000-{tile}.png")
            first = digest_panel_corpus([root])
            Image.new("RGB", (20, 20), "maroon").save(root / "sample-000-center.png")
            self.assertNotEqual(first, digest_panel_corpus([root]))

    def test_writes_owner_only_content_addressed_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            payload = {"format": "zenith-vision.localized-panel-model", "version": 1, "heads": {}}
            path, digest = write_model_bundle(root, payload)
            repeated, repeated_digest = write_model_bundle(root, payload)
            self.assertEqual((path, digest), (repeated, repeated_digest))
            self.assertIn(digest[:16], path.name)
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_region_digest_is_order_independent_for_object_keys(self) -> None:
        left = [{"evidence": "hero", "box": [0, 0, 1, 1]}]
        right = [{"box": [0, 0, 1, 1], "evidence": "hero"}]
        self.assertEqual(region_plan_digest(left), region_plan_digest(right))

    def test_loader_rejects_missing_numeric_heads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            plan = [{"evidence": "hero", "box": [0, 0, 1, 1]}]
            path.write_text(json.dumps({
                "format": "zenith-vision.localized-panel-model", "version": 1,
                "classes": ["hero", "inventory"], "threshold": 0.65,
                "region_plan": plan, "region_plan_sha256": region_plan_digest(plan), "heads": {},
            }))
            with self.assertRaisesRegex(ValueError, "head"):
                load_model_bundle(path)


if __name__ == "__main__":
    unittest.main()
