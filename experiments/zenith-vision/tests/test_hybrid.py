from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.hybrid import combine_panel_evidence


class HybridPanelTests(unittest.TestCase):
    def test_title_evidence_is_preserved(self) -> None:
        result = combine_panel_evidence(frozenset({"inventory"}), {"hero": 0.75, "inventory": 0.99})
        self.assertEqual(result.panels, frozenset({"inventory"}))

    def test_strong_structural_evidence_can_add_overlapping_panel(self) -> None:
        result = combine_panel_evidence(frozenset({"hero"}), {"hero": 0.90, "inventory": 0.60})
        self.assertEqual(result.panels, frozenset({"hero", "inventory"}))

    def test_weak_unanchored_evidence_abstains(self) -> None:
        result = combine_panel_evidence(frozenset(), {"hero": 0.79, "inventory": 0.54})
        self.assertEqual(result.panels, frozenset())
        self.assertEqual(result.source, "abstained")

    def test_validates_score_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly"):
            combine_panel_evidence(frozenset(), {"hero": 0.9})


if __name__ == "__main__":
    unittest.main()
