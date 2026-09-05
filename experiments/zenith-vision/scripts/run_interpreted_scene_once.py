from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from zenith_vision import MumbleSnapshot, TesseractOcr, XWindowCapture, select_exact_window
from zenith_vision.interpreter import interpret_scene
from zenith_vision.live_panels import observe_panels_once
from zenith_vision.scene import build_scene_snapshot

API_ROOT = "http://127.0.0.1:38421"


def read_json(path: str) -> dict[str, Any]:
    request = urllib.request.Request(f"{API_ROOT}{path}", headers={"accept": "application/json"})
    with urllib.request.urlopen(request, timeout=3.0) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Zenith returned a non-object response")
    return payload


def main() -> None:
    now = datetime.now(timezone.utc)
    try:
        telemetry = MumbleSnapshot.from_relay(read_json("/api/player"))
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        telemetry = None
    capture = XWindowCapture()
    target = select_exact_window(capture.list_windows(), title="Guild Wars 2",
        instance="steam_app_1284210", window_class="steam_app_1284210")
    panels = observe_panels_once(capture, target, TesseractOcr(page_segmentation_mode=6), ui_scale="small")
    scene = build_scene_snapshot(telemetry, panels, observed_at=now)
    map_data = None
    map_error = None
    map_id = scene.world.get("map_id") if scene.world else None
    if isinstance(map_id, int):
        try:
            map_data = read_json(f"/api/maps/{map_id}")
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
            map_error = type(error).__name__
    print(json.dumps(interpret_scene(scene, map_data, map_error=map_error).to_dict(), separators=(",", ":")))


if __name__ == "__main__":
    main()
