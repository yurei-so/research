from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.panel_regions import crop_panel_regions, panel_region_plan


class PanelRegionTests(unittest.TestCase):
    def test_plan_is_class_specific_and_stable(self) -> None:
        plan = panel_region_plan()
        self.assertEqual(len(plan), 18)
        self.assertEqual(sum(item.evidence == "hero" for item in plan), 10)
        self.assertEqual(sum(item.evidence == "inventory" for item in plan), 8)
        self.assertEqual(len({item.region_id for item in plan}), len(plan))
        self.assertTrue(all(0 <= value <= 1 for item in plan for value in item.box))

    def test_crops_both_tiles_without_mutating_sources(self) -> None:
        left = Image.new("RGB", (1000, 800), "navy")
        center = Image.new("RGB", (1200, 900), "maroon")
        crops = crop_panel_regions(left, center, evidence="inventory")
        self.assertEqual(len(crops), 8)
        self.assertEqual({region.tile for region, _ in crops}, {"left", "center"})
        self.assertTrue(all(crop.width > 0 and crop.height > 0 for _, crop in crops))
        for _, crop in crops:
            crop.close()
        self.assertEqual(left.getpixel((0, 0)), (0, 0, 128))
        self.assertEqual(center.getpixel((0, 0)), (128, 0, 0))


if __name__ == "__main__":
    unittest.main()
