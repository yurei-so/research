from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import BoundingBox, RegionLabel, RegionProposal, evaluate_regions, propose_default_regions, propose_profile_regions


class LayoutBaselineTests(unittest.TestCase):
    def test_proposes_named_default_regions(self) -> None:
        proposals = propose_default_regions(1920, 1080)
        self.assertEqual({item.kind for item in proposals},
                         {"player_status", "objectives", "chat", "skill_bar", "minimap"})
        self.assertTrue(all(item.source == "gw2_default_layout_baseline" for item in proposals))

    def test_rejects_tiny_and_unsupported_viewports(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least"):
            propose_default_regions(320, 240)
        with self.assertRaisesRegex(ValueError, "aspect"):
            propose_default_regions(800, 800)

    def test_iou_evaluation_matches_by_region_kind(self) -> None:
        proposals = (RegionProposal("minimap", BoundingBox(0.75, 0.7, 0.25, 0.3), 0.5),)
        labels = (RegionLabel("minimap", BoundingBox(0.76, 0.71, 0.23, 0.28)),)
        metrics = evaluate_regions(proposals, labels)
        self.assertEqual(metrics.matched, 1)
        self.assertGreater(metrics.mean_iou, 0.8)

    def test_wrong_kind_does_not_match_same_geometry(self) -> None:
        box = BoundingBox(0.75, 0.7, 0.25, 0.3)
        metrics = evaluate_regions((RegionProposal("chat", box, 0.5),), (RegionLabel("minimap", box),))
        self.assertEqual(metrics.matched, 0)
        self.assertEqual(metrics.mean_iou, 0.0)

    def test_profile_regions_are_frozen_and_explicit(self) -> None:
        normal = propose_profile_regions(1920, 1080, ui_scale="normal")
        self.assertEqual({item.kind for item in normal}, {"objectives", "skill_bar", "minimap"})
        self.assertTrue(all(item.source == "gw2_normal_layout_profile_v1" for item in normal))
        self.assertEqual(next(item.box for item in normal if item.kind == "skill_bar"),
                         BoundingBox(0.30, 0.84, 0.40, 0.16))

    def test_profile_regions_reject_xl(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported UI scale"):
            propose_profile_regions(1920, 1080, ui_scale="larger")


if __name__ == "__main__":
    unittest.main()
