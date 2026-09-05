from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import DatasetManifest, generate_synthetic_corpus


class SyntheticCorpusTests(unittest.TestCase):
    def test_generates_valid_deterministic_split(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_manifest = DatasetManifest.load(generate_synthetic_corpus(Path(first), count=20, seed=7))
            second_manifest = DatasetManifest.load(generate_synthetic_corpus(Path(second), count=20, seed=7))
            self.assertEqual(first_manifest.split_counts(), {"train": 14, "validation": 4, "test": 2})
            self.assertEqual([item.media_sha256 for item in first_manifest.items],
                             [item.media_sha256 for item in second_manifest.items])

    def test_different_seed_changes_media(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a = DatasetManifest.load(generate_synthetic_corpus(Path(first), count=9, seed=1))
            b = DatasetManifest.load(generate_synthetic_corpus(Path(second), count=9, seed=2))
            self.assertNotEqual(a.items[0].media_sha256, b.items[0].media_sha256)

    def test_refuses_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "keep.txt").write_text("owned")
            with self.assertRaises(FileExistsError):
                generate_synthetic_corpus(Path(directory), count=9)


if __name__ == "__main__":
    unittest.main()
