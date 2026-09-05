from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from zenith_vision import MumbleSnapshot, TesseractOcr, XWindowCapture, select_exact_window
from zenith_vision.live_panels import observe_panels_once
from zenith_vision.scene import build_scene_snapshot


def read_telemetry() -> MumbleSnapshot | None:
    request = urllib.request.Request("http://127.0.0.1:38421/api/player", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=2.0) as response:
            return MumbleSnapshot.from_relay(json.load(response))
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return None


def main() -> None:
    capture = XWindowCapture()
    target = select_exact_window(
        capture.list_windows(), title="Guild Wars 2",
        instance="steam_app_1284210", window_class="steam_app_1284210",
    )
    panels = observe_panels_once(
        capture, target, TesseractOcr(page_segmentation_mode=6), ui_scale="small",
    )
    scene = build_scene_snapshot(read_telemetry(), panels, observed_at=datetime.now(timezone.utc))
    print(json.dumps(scene.to_dict(), separators=(",", ":")))


if __name__ == "__main__":
    main()
