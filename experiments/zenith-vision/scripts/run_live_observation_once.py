import hashlib
import json
import os
import urllib.request
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from zenith_vision import (
    MumbleSnapshot, OcrFailure, TesseractOcr, XWindowCapture, fuse_observations,
    interpret_objectives_crop, objective_text_to_vision, persist_profile_crops,
    save_objective_observation, select_exact_window,
)

started = datetime.now(timezone.utc)
run = Path.home() / ".local/state/zenith-vision/live-observations" / started.strftime("normal-%Y%m%dT%H%M%SZ")
capture = XWindowCapture()
target = select_exact_window(
    capture.list_windows(), title="Guild Wars 2",
    instance="steam_app_1284210", window_class="steam_app_1284210",
)
frame = capture.capture(target)
receipt_path, receipt = persist_profile_crops(frame, run / "crops", ui_scale="normal", now=started)
frame.close()
del frame

artifact = next(item for item in receipt.artifacts if item.kind == "objectives")
crop_path = receipt_path.parent / artifact.file
digest = hashlib.sha256(crop_path.read_bytes()).hexdigest()
if digest != artifact.sha256:
    raise RuntimeError("objectives crop digest mismatch")
objective = None
objective_status = "accepted"
try:
    with Image.open(crop_path) as crop:
        objective = interpret_objectives_crop(
            crop, TesseractOcr(), captured_at=started.isoformat(), source_crop_sha256=digest,
        )
    save_objective_observation(objective, run / "objective-observation.json")
except OcrFailure:
    objective_status = "rejected_fail_closed"

request = urllib.request.Request("http://127.0.0.1:38421/api/player", method="GET")
with urllib.request.urlopen(request, timeout=2.0) as response:
    payload = json.load(response)
telemetry = replace(MumbleSnapshot.from_relay(payload), character_name=None)
fused_at = datetime.now(timezone.utc)
visual = (objective_text_to_vision(objective),) if objective is not None else ()
fused = fuse_observations(telemetry, visual, now=fused_at)
destination = run / "fused-observation.json"
temporary = destination.with_name(".fused-observation.json.tmp")
temporary.write_text(json.dumps(asdict(fused), indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, destination)
print(json.dumps({
    "status": "ok", "ui_scale": "normal", "window_identity_verified": True,
    "crop_kinds": [item.kind for item in receipt.artifacts],
    "full_frame_persisted": receipt.source_artifact_written,
    "objective_status": objective_status,
    "objective_tokens_retained": objective.token_count if objective else 0,
    "objective_tokens_rejected": objective.rejected_token_count if objective else 0,
    "objective_confidence": round(objective.confidence, 6) if objective else None,
    "objective_complete": objective.complete if objective else False,
    "telemetry_status": fused.telemetry_status,
    "telemetry_source": telemetry.source,
    "map_available": telemetry.map_id is not None,
    "position_available": telemetry.position is not None,
    "heading_available": telemetry.heading is not None,
    "character_name_persisted": False,
    "visual_observations": len(fused.visual),
    "rejected_visual_observations": len(fused.rejected_visual),
}, separators=(",", ":")))
