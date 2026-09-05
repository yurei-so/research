from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from zenith_vision import (
    TesseractOcr, XWindowCapture, mask_regions, scan_panel_titles,
    select_exact_window, structural_privacy_regions,
)
from zenith_vision.panel_collection import artifacts_to_dict, persist_panel_sample, write_panel_batch_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a bounded private GW2 panel-recognition batch")
    parser.add_argument("destination", type=Path)
    parser.add_argument("--count", type=int, default=15)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--ui-scale", choices=("small",), default="small")
    parser.add_argument("--skip-recognition", action="store_true")
    parser.add_argument("--purpose", choices=("development", "holdout"), default="development")
    args = parser.parse_args()
    if not 1 <= args.count <= 60:
        raise SystemExit("count must be between 1 and 60")
    if not 0.25 <= args.interval <= 30:
        raise SystemExit("interval must be between 0.25 and 30 seconds")
    if args.destination.exists():
        raise SystemExit("destination must not already exist")
    args.destination.mkdir(parents=True, mode=0o700)
    started = datetime.now(timezone.utc)
    capture = XWindowCapture()
    target = select_exact_window(
        capture.list_windows(), title="Guild Wars 2",
        instance="steam_app_1284210", window_class="steam_app_1284210",
    )
    ocr = TesseractOcr(page_segmentation_mode=6)
    items: list[dict[str, object]] = []
    for index in range(args.count):
        frame = capture.capture(target)
        masked = mask_regions(frame, structural_privacy_regions(args.ui_scale))
        frame.close()
        observation = None if args.skip_recognition else scan_panel_titles(masked, ocr)
        artifacts = persist_panel_sample(masked, args.destination, sample_id=f"sample-{index:03d}")
        masked.close()
        items.append({
            "id": f"sample-{index:03d}", "captured_at": datetime.now(timezone.utc).isoformat(),
            "observation": ({"status": observation.status, "panels": list(observation.panels),
                             "confidence": observation.confidence} if observation is not None else None),
            "artifacts": artifacts_to_dict(artifacts),
        })
        write_panel_batch_manifest(args.destination, {
            "format": "zenith-vision.panel-chaos-batch", "version": 1,
            "status": ("collecting" if index + 1 < args.count else
                       "frozen_holdout_pending_labels" if args.purpose == "holdout" else
                       "development_pending_labels"),
            "started_at": started.isoformat(), "ui_scale": args.ui_scale,
            "privacy_mask": "chat-and-party-structural-v1", "source_class": "private_operator",
            "license": "private-not-for-release", "source_frame_persisted": False,
            "recognition_run_during_capture": not args.skip_recognition,
            "purpose": args.purpose,
            "candidate_count": len(items), "items": items,
        })
        if index + 1 < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
