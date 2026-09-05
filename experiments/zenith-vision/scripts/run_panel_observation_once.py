from __future__ import annotations

import json
from dataclasses import asdict

from zenith_vision import TesseractOcr, XWindowCapture, select_exact_window
from zenith_vision.live_panels import observe_panels_once


def main() -> None:
    capture = XWindowCapture()
    target = select_exact_window(
        capture.list_windows(), title="Guild Wars 2",
        instance="steam_app_1284210", window_class="steam_app_1284210",
    )
    observation = observe_panels_once(
        capture, target, TesseractOcr(page_segmentation_mode=6), ui_scale="small",
    )
    print(json.dumps(asdict(observation), separators=(",", ":")))


if __name__ == "__main__":
    main()
