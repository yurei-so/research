from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import WindowIdentity, WindowSelectionError, parse_wm_class, select_exact_window


class WindowIdentityTests(unittest.TestCase):
    def test_parses_xprop_identity(self) -> None:
        self.assertEqual(parse_wm_class('WM_CLASS(STRING) = "steam_app_1284210", "steam_app_1284210"\n'),
                         ("steam_app_1284210", "steam_app_1284210"))

    def test_rejects_malformed_or_multiline_identity(self) -> None:
        with self.assertRaises(WindowSelectionError):
            parse_wm_class('WM_CLASS: not found.\n')
        with self.assertRaises(WindowSelectionError):
            parse_wm_class('WM_CLASS(STRING) = "safe", "safe"\nINJECTED')

    def test_exact_selection_uses_title_instance_and_class(self) -> None:
        target = WindowIdentity(10, "Guild Wars 2", "steam_app_1284210", "steam_app_1284210")
        decoy = WindowIdentity(11, "Guild Wars 2", "decoy", "decoy")
        self.assertEqual(select_exact_window((decoy, target), title=target.title,
                                             instance=target.instance, window_class=target.window_class), target)

    def test_missing_or_ambiguous_selection_fails_closed(self) -> None:
        target = WindowIdentity(10, "Guild Wars 2", "steam_app_1284210", "steam_app_1284210")
        with self.assertRaisesRegex(WindowSelectionError, "not available"):
            select_exact_window((), title=target.title, instance=target.instance, window_class=target.window_class)
        with self.assertRaisesRegex(WindowSelectionError, "ambiguous"):
            select_exact_window((target, target), title=target.title,
                                instance=target.instance, window_class=target.window_class)


if __name__ == "__main__":
    unittest.main()
