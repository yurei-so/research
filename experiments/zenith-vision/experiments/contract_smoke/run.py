from __future__ import annotations

import json
from datetime import datetime, timezone

from zenith_vision import MumbleSnapshot, VisionObservation, fuse_observations

now = datetime(2026, 8, 24, 12, 0, 1, tzinfo=timezone.utc)
telemetry = MumbleSnapshot.from_relay({
    "type": "player", "sequence": 42, "connected": True, "mapId": 15,
    "position": [1234.5, 678.9], "heading": 1.25, "characterName": "Synthetic Character",
    "timestamp": "2026-08-24T12:00:00Z", "source": "mock", "inCombat": False,
})
fused = fuse_observations(telemetry, [
    VisionObservation("ui_icon", "synthetic-condition", 0.95, "2026-08-24T12:00:00Z"),
    VisionObservation("map", "wrong-visual-map", 0.99, "2026-08-24T12:00:00Z"),
], now=now)
assert fused.player is not None and fused.player["map_id"] == 15
assert len(fused.visual) == 1
assert fused.rejected_visual[0]["reason"] == "reserved_for_telemetry"
print(json.dumps({
    "format": "zenith-vision.experiment-result", "version": 1,
    "experiment": "contract_smoke", "status": "ok",
    "checks": {"telemetry_authoritative": True, "non_telemetry_vision_preserved": True,
               "conflicting_visual_guess_rejected": True},
}, separators=(",", ":")))
