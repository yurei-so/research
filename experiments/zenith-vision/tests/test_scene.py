from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.models import MumbleSnapshot
from zenith_vision.panels import PanelObservation
from zenith_vision.scene import build_scene_snapshot


NOW = datetime(2026, 8, 25, 12, 0, 1, tzinfo=timezone.utc)


class SceneSnapshotTests(unittest.TestCase):
    def test_combines_authoritative_world_and_allowlisted_ui(self) -> None:
        telemetry = MumbleSnapshot(
            sequence=1, connected=True, map_id=15, position=(1.0, 2.0), heading=0.5,
            character_name="Withheld Name", timestamp="2026-08-25T12:00:00Z", in_combat=True,
        )
        panels = PanelObservation(
            "zenith-vision.panel-observation", 1, ("inventory",), "recognized", 0.98,
            "fake", "chat-masked-panel-title-allowlist-v1",
        )
        scene = build_scene_snapshot(telemetry, panels, observed_at=NOW)
        self.assertEqual(scene.telemetry_status, "current")
        self.assertEqual(scene.world["map_id"], 15)  # type: ignore[index]
        self.assertIsNone(scene.world["character_name"])  # type: ignore[index]
        self.assertEqual(scene.ui["panels"], ["inventory"])
        self.assertIn("raw_frame", scene.withheld)
        self.assertNotIn("Withheld Name", str(scene.to_dict()))

    def test_ui_survives_missing_telemetry_without_world_guess(self) -> None:
        panels = PanelObservation(
            "zenith-vision.panel-observation", 1, (), "none", 1.0,
            "fake", "chat-masked-panel-title-allowlist-v1",
        )
        scene = build_scene_snapshot(None, panels, observed_at=NOW)
        self.assertEqual(scene.telemetry_status, "missing")
        self.assertIsNone(scene.world)
        self.assertEqual(scene.ui["panel_status"], "none")


if __name__ == "__main__":
    unittest.main()
