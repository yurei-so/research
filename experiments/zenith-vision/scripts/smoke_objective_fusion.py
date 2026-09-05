import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from zenith_vision import MumbleSnapshot, ObjectiveTextObservation, fuse_observations, objective_text_to_vision

root = Path.home() / ".local/state/zenith-vision/runtime-crops"
run = sorted(path for path in root.glob("normal-*") if (path / "objective-observation.json").is_file())[-1]
objective = ObjectiveTextObservation(**json.loads(
    (run / "objective-observation.json").read_text(encoding="utf-8")
))
observed = datetime.now(timezone.utc)
telemetry = MumbleSnapshot(
    sequence=1, connected=True, map_id=0, position=(0.0, 0.0), heading=0.0,
    character_name=None, timestamp=observed.isoformat(), source="mock",
)
fused = fuse_observations(telemetry, (objective_text_to_vision(objective),), now=observed)
destination = run / "fused-observation.json"
temporary = destination.with_name(".fused-observation.json.tmp")
temporary.write_text(json.dumps(asdict(fused), indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, destination)
print(json.dumps({
    "status": "ok", "telemetry_status": fused.telemetry_status,
    "visual_count": len(fused.visual), "rejected_visual_count": len(fused.rejected_visual),
    "has_evidence": fused.visual[0].evidence is not None,
}, separators=(",", ":")))
