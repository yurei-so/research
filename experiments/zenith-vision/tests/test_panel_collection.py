from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.panel_collection import extract_panel_search_tiles, persist_panel_sample


class PanelCollectionTests(unittest.TestCase):
    def test_extracts_overlapping_left_and_center_tiles(self) -> None:
        tiles = extract_panel_search_tiles(Image.new("RGB", (1000, 500)))
        self.assertEqual(tiles["left"].size, (600, 370))
        self.assertEqual(tiles["center"].size, (650, 350))
        for tile in tiles.values():
            tile.close()

    def test_persists_owner_only_tiles_without_source_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "samples"
            artifacts = persist_panel_sample(Image.new("RGB", (1000, 500), "navy"), root, sample_id="sample-00")
            self.assertEqual({item.kind for item in artifacts}, {"left", "center"})
            self.assertEqual({path.name for path in root.iterdir()}, {"sample-00-left.png", "sample-00-center.png"})
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertTrue(all((os.stat(root / item.file).st_mode & 0o777) == 0o600 for item in artifacts))

    def test_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frame = Image.new("RGB", (1000, 500))
            persist_panel_sample(frame, root, sample_id="same")
            with self.assertRaises(FileExistsError):
                persist_panel_sample(frame, root, sample_id="same")


if __name__ == "__main__":
    unittest.main()
