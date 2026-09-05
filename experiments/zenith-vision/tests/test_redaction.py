from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import BoundingBox, RevealDecision, mask_regions, reverse_reveal


class ReverseRevealTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGB", (100, 100), (250, 100, 50))

    def test_no_decisions_produces_fully_redacted_frame(self) -> None:
        result, receipt = reverse_reveal(self.image, [])
        self.assertEqual(result.getbbox(), None)
        self.assertEqual(receipt.revealed_pixels, 0)

    def test_only_approved_region_is_copied(self) -> None:
        decision = RevealDecision(BoundingBox(0.25, 0.25, 0.5, 0.5), "game_world", "fixture", 1.0)
        result, receipt = reverse_reveal(self.image, [decision])
        self.assertEqual(result.getpixel((50, 50)), (250, 100, 50))
        self.assertEqual(result.getpixel((10, 10)), (0, 0, 0))
        self.assertEqual(receipt.revealed_pixels, 2500)
        self.assertEqual(receipt.revealed_fraction, 0.25)

    def test_low_confidence_decision_reveals_nothing(self) -> None:
        decision = RevealDecision(BoundingBox(0, 0, 1, 1), "non_sensitive_ui", "fixture", 0.94)
        result, receipt = reverse_reveal(self.image, [decision])
        self.assertEqual(result.getbbox(), None)
        self.assertEqual(receipt.decisions_applied, 0)
        self.assertEqual(receipt.decisions_rejected, 1)

    def test_overlapping_regions_are_counted_once(self) -> None:
        decisions = [
            RevealDecision(BoundingBox(0, 0, 0.5, 0.5), "game_world", "a", 1.0),
            RevealDecision(BoundingBox(0.25, 0.25, 0.5, 0.5), "game_world", "b", 1.0),
        ]
        _, receipt = reverse_reveal(self.image, decisions)
        self.assertEqual(receipt.revealed_pixels, 4375)

    def test_masks_complete_structural_regions(self) -> None:
        result = mask_regions(self.image, [BoundingBox(0, 0.5, 0.5, 0.5)])
        self.assertEqual(result.getpixel((25, 75)), (0, 0, 0))
        self.assertEqual(result.getpixel((75, 75)), (250, 100, 50))

    def test_chat_mask_can_leave_skill_bar_safety_gap(self) -> None:
        source = Image.new("RGB", (1000, 1000), "white")
        result = mask_regions(source, [BoundingBox(0.0, 0.66, 0.30, 0.34)])
        self.assertEqual(result.getpixel((299, 900)), (0, 0, 0))
        self.assertEqual(result.getpixel((315, 900)), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
