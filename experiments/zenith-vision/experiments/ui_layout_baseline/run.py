from __future__ import annotations

import json
from pathlib import Path

from zenith_vision import BoundingBox, RegionLabel, evaluate_regions, propose_default_regions

fixture = json.loads((Path(__file__).with_name("fixture.json")).read_text(encoding="utf-8"))
viewport = fixture["viewport"]
labels = tuple(RegionLabel(item["kind"], BoundingBox(*item["box"])) for item in fixture["labels"])
metrics = evaluate_regions(propose_default_regions(viewport["width"], viewport["height"]), labels)
status = "ok" if metrics.recall_at_50 == 1.0 and metrics.mean_iou >= 0.70 else "failed"
print(json.dumps({
    "format": "zenith-vision.experiment-result", "version": 1,
    "experiment": "ui_layout_baseline", "status": status,
    "metrics": {"matched": metrics.matched, "expected": metrics.expected,
                "proposed": metrics.proposed, "mean_iou": round(metrics.mean_iou, 6),
                "recall_at_50": round(metrics.recall_at_50, 6)},
}, separators=(",", ":")))
raise SystemExit(0 if status == "ok" else 1)
