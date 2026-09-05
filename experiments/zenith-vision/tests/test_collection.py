from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import create_contact_sheet, difference_hash, hamming_distance, is_distinct, structural_privacy_regions


class CollectionTests(unittest.TestCase):
    def test_hash_is_deterministic_and_distance_is_symmetric(self) -> None:
        image = Image.new("RGB", (100, 100), "white")
        value = difference_hash(image)
        self.assertEqual(value, difference_hash(image.copy()))
        self.assertEqual(hamming_distance(value, 0), hamming_distance(0, value))

    def test_distinct_gate_rejects_near_duplicate(self) -> None:
        self.assertFalse(is_distinct(0b0011, [0b0001], minimum_distance=2))
        self.assertTrue(is_distinct(0b1111, [0b0000], minimum_distance=4))

    def test_contact_sheet_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "a.png", root / "b.png"
            Image.new("RGB", (100, 50), "red").save(first)
            Image.new("RGB", (100, 50), "blue").save(second)
            sheet = create_contact_sheet([("01", first), ("02", second)], root / "sheet.png")
            self.assertEqual(stat.S_IMODE(sheet.stat().st_mode), 0o600)
            with Image.open(sheet) as image:
                self.assertEqual(image.size, (960, 298))

    def test_large_profile_masks_taller_chat_without_reaching_skill_bar(self) -> None:
        chat, _ = structural_privacy_regions("large")
        self.assertEqual((chat.y, chat.height), (0.52, 0.48))
        self.assertEqual(chat.x + chat.width, 0.30)

    def test_unknown_ui_profile_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported UI scale"):
            structural_privacy_regions("unknown")


if __name__ == "__main__":
    unittest.main()
