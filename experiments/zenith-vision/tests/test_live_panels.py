from __future__ import annotations

import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.capture import WindowIdentity
from zenith_vision.live_panels import observe_panels_once
from zenith_vision.ocr import OcrScan, OcrToken


class FakeCapture:
    def __init__(self) -> None:
        self.frame = Image.new("RGB", (1000, 600), "white")

    def capture(self, identity: WindowIdentity) -> Image.Image:
        return self.frame.copy()


class FakeOcr:
    def scan(self, image: Image.Image) -> OcrScan:
        return OcrScan(tokens=(OcrToken("Inventory", 0.99),), backend="fake", complete=True)


class LivePanelTests(unittest.TestCase):
    def test_returns_only_allowlisted_observation(self) -> None:
        result = observe_panels_once(
            FakeCapture(), WindowIdentity(1, "Guild Wars 2", "steam_app_1284210", "steam_app_1284210"),
            FakeOcr(), ui_scale="small",
        )
        self.assertEqual(result.panels, ("inventory",))
        self.assertEqual(result.status, "recognized")
        self.assertEqual(result.disclosure_policy, "chat-masked-panel-title-allowlist-v1")
