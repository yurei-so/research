from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.ui_state import UiStateBaseline, UiStateExample, extract_ui_state_features


def fixture(*, visible: bool, shade: int = 35) -> Image.Image:
    image = Image.new("RGB", (160, 80), (shade, shade, shade))
    if visible:
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 152, 72), radius=8, fill=(80, 75, 65), outline=(230, 220, 190), width=3)
        for y in (24, 40, 56):
            draw.rectangle((22, y, 132, y + 3), fill=(215, 210, 190))
    return image


class UiStateBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        examples = []
        for visible, state in ((True, "present"), (False, "absent")):
            for shade in (30, 40, 50):
                examples.append(UiStateExample("objectives", state, extract_ui_state_features(
                    fixture(visible=visible, shade=shade))))
        self.baseline = UiStateBaseline(examples, abstain_margin=0.10)

    def test_recognizes_visible_panel(self) -> None:
        result = self.baseline.recognize(fixture(visible=True, shade=45), region="objectives")
        self.assertEqual(result.state, "present")
        self.assertGreater(result.confidence, 0.10)

    def test_recognizes_absent_panel(self) -> None:
        result = self.baseline.recognize(fixture(visible=False, shade=45), region="objectives")
        self.assertEqual(result.state, "absent")

    def test_abstains_at_midpoint(self) -> None:
        ambiguous = extract_ui_state_features(fixture(visible=False, shade=40))
        examples = [UiStateExample("minimap", "present", ambiguous), UiStateExample("minimap", "absent", ambiguous)]
        baseline = UiStateBaseline(examples, abstain_margin=0.10)
        self.assertEqual(baseline.recognize(fixture(visible=False, shade=40), region="minimap").state, "uncertain")

    def test_requires_both_classes(self) -> None:
        baseline = UiStateBaseline([UiStateExample(
            "skill_bar", "present", extract_ui_state_features(fixture(visible=True)))])
        with self.assertRaisesRegex(ValueError, "present and absent"):
            baseline.recognize(fixture(visible=True), region="skill_bar")

    def test_rejects_tiny_crop(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 16x16"):
            extract_ui_state_features(Image.new("RGB", (8, 8)))


if __name__ == "__main__":
    unittest.main()
