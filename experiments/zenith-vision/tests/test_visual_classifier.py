from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.visual_classifier import (
    LabeledPanelSample, evaluate_panel_model, extract_local_panel_features,
    extract_panel_features, train_ridge_panel_model,
)


def features(hero: bool, inventory: bool, shade: int) -> object:
    left = Image.new("RGB", (800, 500), (shade, shade, shade))
    center = left.copy()
    if hero:
        draw = ImageDraw.Draw(left)
        draw.rectangle((180, 40, 500, 460), fill=(45, 42, 34), outline="white", width=3)
        for y in range(80, 420, 45): draw.ellipse((190, y, 210, y + 20), outline="gold", width=2)
    if inventory:
        draw = ImageDraw.Draw(center)
        draw.rectangle((300, 100, 740, 470), fill=(35, 32, 28), outline="white", width=3)
        for x in range(320, 700, 45):
            for y in range(150, 430, 45): draw.rectangle((x, y, x + 32, y + 32), outline="gold")
    return extract_panel_features(left, center)


class VisualClassifierTests(unittest.TestCase):
    def test_learns_independent_panel_states(self) -> None:
        samples = tuple(
            LabeledPanelSample(f"{hero}-{inventory}-{shade}", features(hero, inventory, shade),
                               frozenset(kind for kind, active in (("hero", hero), ("inventory", inventory)) if active))
            for hero in (False, True) for inventory in (False, True) for shade in (20, 35, 50)
        )
        model = train_ridge_panel_model(samples)
        result = evaluate_panel_model(model, samples)
        self.assertEqual(result["exact_accuracy"], 1.0)

    def test_requires_enough_samples(self) -> None:
        with self.assertRaisesRegex(ValueError, "four"):
            train_ridge_panel_model((LabeledPanelSample("one", features(False, False, 20), frozenset()),))

    def test_local_features_ignore_panel_translation(self) -> None:
        base = Image.new("RGB", (800, 500), "gray")
        moved = base.copy()
        ImageDraw.Draw(base).rectangle((100, 100, 300, 400), fill="black", outline="gold", width=3)
        ImageDraw.Draw(moved).rectangle((400, 100, 600, 400), fill="black", outline="gold", width=3)
        static = Image.new("RGB", (800, 500), "gray")
        left = extract_local_panel_features(base, static)
        right = extract_local_panel_features(moved, static)
        self.assertLess(float(abs(left - right).mean()), 0.02)


if __name__ == "__main__":
    unittest.main()
