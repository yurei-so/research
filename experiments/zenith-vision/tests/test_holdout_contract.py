from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.holdout_contract import resolve_holdout_directories


class HoldoutContractTests(unittest.TestCase):
    def test_resolves_four_distinct_child_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ("one-001", "two-002", "three-003", "four-004")
            for name in names:
                (root / name).mkdir()
            self.assertEqual(
                resolve_holdout_directories(root, ",".join(names)),
                tuple((root / name).resolve() for name in names),
            )

    def test_rejects_duplicates_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one").mkdir()
            with self.assertRaisesRegex(ValueError, "distinct"):
                resolve_holdout_directories(root, "one,one,one,one")
            with self.assertRaisesRegex(ValueError, "invalid"):
                resolve_holdout_directories(root, "one,two,three,../escape")
