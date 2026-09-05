from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import MumbleSnapshot, VisionObservation, fuse_observations

NOW = datetime(2026, 8, 24, 12, 0, 1, tzinfo=timezone.utc)


def snapshot(**overrides: object) -> MumbleSnapshot:
    values: dict[str, object] = {"sequence": 4, "connected": True, "map_id": 15,
        "position": (10.0, 20.0), "heading": 0.5, "character_name": "Fixture",
        "timestamp": "2026-08-24T12:00:00Z", "source": "mock"}
    values.update(overrides)
    return MumbleSnapshot(**values)  # type: ignore[arg-type]


class FusionTests(unittest.TestCase):
    def test_telemetry_is_authoritative_and_conflicts_are_rejected(self) -> None:
        result = fuse_observations(snapshot(), [
            VisionObservation("map", "visual guess", 0.99, "2026-08-24T12:00:00Z"),
            VisionObservation("ui_icon", "bleeding", 0.90, "2026-08-24T12:00:00Z"),
        ], now=NOW)
        self.assertEqual(result.player["map_id"], 15)  # type: ignore[index]
        self.assertEqual([item.label for item in result.visual], ["bleeding"])
        self.assertEqual(result.rejected_visual[0]["reason"], "reserved_for_telemetry")
        self.assertNotIn("label", result.rejected_visual[0])

    def test_accepted_visual_evidence_survives_fusion(self) -> None:
        observation = VisionObservation(
            "objective_text", "Complete the event", 0.9, "2026-08-24T12:00:00Z",
            evidence={"disclosure_policy": "operator-approved-objectives-text-v1"},
        )
        result = fuse_observations(snapshot(), [observation], now=NOW)
        self.assertEqual(result.visual[0].evidence["disclosure_policy"],
                         "operator-approved-objectives-text-v1")  # type: ignore[index]

    def test_stale_telemetry_does_not_leak_state_or_enable_visual_guess(self) -> None:
        result = fuse_observations(snapshot(timestamp="2026-08-24T11:59:00Z"), [
            VisionObservation("location", "some wall", 0.75, "2026-08-24T12:00:00Z")], now=NOW)
        self.assertEqual(result.telemetry_status, "stale")
        self.assertIsNone(result.player)
        self.assertEqual(len(result.rejected_visual), 1)

    def test_disconnected_and_missing_telemetry_are_explicit(self) -> None:
        disconnected = fuse_observations(snapshot(connected=False), [], now=NOW)
        missing = fuse_observations(None, [], now=NOW)
        self.assertEqual(disconnected.telemetry_status, "disconnected")
        self.assertEqual(missing.telemetry_status, "missing")
        self.assertIsNone(disconnected.player)
        self.assertIsNone(missing.player)

    def test_future_timestamp_is_stale(self) -> None:
        result = fuse_observations(snapshot(timestamp="2026-08-24T12:00:10Z"), [], now=NOW,
                                   max_telemetry_age=timedelta(seconds=2))
        self.assertEqual(result.telemetry_status, "stale")

    def test_relay_payload_matches_zenith_camel_case_contract(self) -> None:
        parsed = MumbleSnapshot.from_relay({"type": "player", "sequence": 1, "connected": True,
            "mapId": 99, "position": [1, 2], "heading": 0, "characterName": "Test",
            "timestamp": "2026-08-24T12:00:00Z", "source": "mumblelink", "cameraFront": [0, 0, -1]})
        self.assertEqual(parsed.map_id, 99)
        self.assertEqual(parsed.position, (1.0, 2.0))
        self.assertEqual(parsed.camera_front, (0.0, 0.0, -1.0))


if __name__ == "__main__":
    unittest.main()
