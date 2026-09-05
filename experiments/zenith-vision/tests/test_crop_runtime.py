from __future__ import annotations

import hashlib
import json
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import persist_profile_crops


class CropRuntimeTests(unittest.TestCase):
    def test_persists_only_three_private_crops_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_path, receipt = persist_profile_crops(
                Image.new("RGB", (1920, 1080), "navy"), root / "run",
                ui_scale="normal", now=datetime(2026, 8, 25, tzinfo=timezone.utc),
            )
            self.assertEqual({item.kind for item in receipt.artifacts},
                             {"objectives", "skill_bar", "minimap"})
            self.assertFalse(receipt.source_artifact_written)
            self.assertEqual({path.name for path in (root / "run").iterdir()},
                             {"objectives.png", "skill_bar.png", "minimap.png", "receipt.json"})
            self.assertEqual(stat.S_IMODE((root / "run").stat().st_mode), 0o700)
            for artifact in receipt.artifacts:
                path = root / "run" / artifact.file
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact.sha256)
            self.assertEqual(json.loads(receipt_path.read_text())["profile_source"],
                             "gw2_normal_layout_profile_v1")

    def test_rejects_unpromoted_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "not promoted"):
                persist_profile_crops(Image.new("RGB", (1920, 1080)), Path(directory), ui_scale="small")

    def test_refuses_nonempty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "existing").write_text("keep")
            with self.assertRaisesRegex(FileExistsError, "empty"):
                persist_profile_crops(Image.new("RGB", (1920, 1080)), root, ui_scale="normal")


if __name__ == "__main__":
    unittest.main()
