from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision.interpreter import interpret_scene
from zenith_vision.models import MumbleSnapshot
from zenith_vision.panels import PanelObservation
from zenith_vision.scene import build_scene_snapshot

NOW = datetime(2026, 8, 25, 12, 0, 1, tzinfo=timezone.utc)


def make_scene(*, combat: bool | None = False, panels: tuple[str, ...] = ()):
    telemetry = MumbleSnapshot(sequence=1, connected=True, map_id=15, position=(100.0, 200.0),
        heading=0.5, character_name="Secret", timestamp="2026-08-25T12:00:00Z", in_combat=combat)
    observed = PanelObservation("zenith-vision.panel-observation", 1, panels,
        "recognized" if panels else "none", 0.99, "fake", "chat-masked-panel-title-allowlist-v1")
    return build_scene_snapshot(telemetry, observed, observed_at=NOW)


MAP = {"id": 15, "name": "Queensdale", "regionName": "Kryta", "continentName": "Tyria",
    "minLevel": 1, "maxLevel": 17,
    "pointsOfInterest": [{"id": 1, "name": "Near Waypoint", "kind": "waypoint", "coordinate": [103, 204]},
                         {"id": 2, "name": "Far Vista", "kind": "vista", "coordinate": [200, 300]}],
    "hearts": [{"id": 3, "name": "Nearby Heart", "coordinate": [110, 200]}]}


class InterpreterTests(unittest.TestCase):
    def test_resolves_map_and_nearby_context_without_identity(self) -> None:
        result = interpret_scene(make_scene(panels=("inventory",)), MAP)
        self.assertEqual(result.map_context["name"], "Queensdale")
        self.assertEqual(result.nearby[0]["name"], "Near Waypoint")
        self.assertEqual(result.nearby[0]["distance_game_units"], 5.0)
        self.assertEqual(result.situation["ui_focus"], "inventory")
        self.assertNotIn("Secret", str(result.to_dict()))
        self.assertIn("raw_prompt", result.withheld)

    def test_combat_guidance_wins_over_panel_management(self) -> None:
        result = interpret_scene(make_scene(combat=True, panels=("hero",)), MAP)
        self.assertEqual(result.situation["mode"], "combat")
        self.assertEqual(result.guidance[0]["kind"], "combat_safe")

    def test_wrong_map_payload_abstains(self) -> None:
        result = interpret_scene(make_scene(), dict(MAP, id=999))
        self.assertEqual(result.map_context["status"], "unavailable")
        self.assertIn("map_context", result.unknowns)
        self.assertEqual(result.provenance["map"], "unavailable")

    def test_missing_telemetry_withholds_world_guidance(self) -> None:
        panels = PanelObservation("zenith-vision.panel-observation", 1, (), "none", 1.0,
            "fake", "chat-masked-panel-title-allowlist-v1")
        result = interpret_scene(build_scene_snapshot(None, panels, observed_at=NOW), None)
        self.assertEqual(result.situation["mode"], "world_state_unavailable")
        self.assertEqual(result.guidance[0]["kind"], "wait_for_telemetry")
        self.assertEqual(result.nearby, ())

    def test_nearby_limit_is_bounded(self) -> None:
        self.assertEqual(len(interpret_scene(make_scene(), MAP, nearby_limit=1).nearby), 1)
        with self.assertRaises(ValueError):
            interpret_scene(make_scene(), MAP, nearby_limit=-1)


if __name__ == "__main__":
    unittest.main()
