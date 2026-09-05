import hashlib
import json
from pathlib import Path

from PIL import Image

from zenith_vision import TesseractOcr, interpret_objectives_crop, save_objective_observation

root = Path.home() / ".local/state/zenith-vision/runtime-crops"
runs = sorted(path for path in root.glob("normal-*") if path.is_dir())
if not runs:
    raise RuntimeError("no private Normal crop run is available")
run = runs[-1]
receipt = json.loads((run / "receipt.json").read_text(encoding="utf-8"))
artifact = next(item for item in receipt["artifacts"] if item["kind"] == "objectives")
crop = run / artifact["file"]
digest = hashlib.sha256(crop.read_bytes()).hexdigest()
if digest != artifact["sha256"]:
    raise RuntimeError("objectives crop digest mismatch")
with Image.open(crop) as image:
    observation = interpret_objectives_crop(
        image, TesseractOcr(), captured_at=receipt["created_at"], source_crop_sha256=digest,
    )
destination = save_objective_observation(observation, run / "objective-observation.json")
print(json.dumps({
    "status": "ok", "observation": destination.name,
    "token_count": observation.token_count, "confidence": round(observation.confidence, 6),
    "rejected_token_count": observation.rejected_token_count,
    "retained_fraction": round(observation.retained_fraction, 6),
    "complete": observation.complete,
    "backend": observation.backend, "policy": observation.disclosure_policy,
}, separators=(",", ":")))
