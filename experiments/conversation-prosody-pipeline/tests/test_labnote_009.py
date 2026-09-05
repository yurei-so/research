import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).parents[1] / "experiments" / "labnote_009"
sys.path.insert(0, str(EXPERIMENT_DIR))

from run_native_stress import annotate_competing_focus, validate_phoneme_contrast  # noqa: E402


@dataclass
class Token:
    text: str
    phonemes: str


class Labnote009Tests(unittest.TestCase):
    def test_annotation_targets_exactly_one_whole_word(self):
        self.assertEqual(annotate_competing_focus("She ordered the blue curtains.", "blue"),
                         "She ordered the [blue](-1) curtains.")
        with self.assertRaises(ValueError):
            annotate_competing_focus("Blue blue.", "blue")

    def test_manifest_allows_only_competing_stress_demotion(self):
        plain = [Token("She", "ʃˈi"), Token("blue", "blˈu")]
        variant = [Token("She", "ʃˈi"), Token("blue", "blˌu")]
        result = validate_phoneme_contrast(plain, variant, "She", "blue")
        self.assertEqual(result["changed_token_count"], 1)

    def test_manifest_rejects_nonfocus_changes(self):
        plain = [Token("She", "ʃˈi"), Token("blue", "blˈu"), Token("curtains", "kˈɜ")]
        variant = [Token("She", "ʃˈi"), Token("blue", "blˌu"), Token("curtains", "kˌɜ")]
        with self.assertRaises(ValueError):
            validate_phoneme_contrast(plain, variant, "She", "blue")


if __name__ == "__main__":
    unittest.main()
