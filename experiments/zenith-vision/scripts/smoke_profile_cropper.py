import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from zenith_vision import persist_profile_crops

state = Path.home() / ".local/state/zenith-vision"
dataset = state / "datasets/operator-normal-validation-v1"
manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
source = dataset / manifest["items"][0]["media"]
run = state / "runtime-crops" / datetime.now(timezone.utc).strftime("normal-%Y%m%dT%H%M%SZ")
with Image.open(source) as frame:
    receipt_path, receipt = persist_profile_crops(frame, run, ui_scale="normal")
print(json.dumps({
    "status": "ok", "receipt": str(receipt_path),
    "artifacts": [{"kind": item.kind, "width": item.width, "height": item.height}
                  for item in receipt.artifacts],
}, separators=(",", ":")))
