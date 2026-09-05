import json
import os
from pathlib import Path

from zenith_vision import RegionLabel, evaluate_regions, extract_blind_boxes, propose_profile_regions

root = Path.home() / ".local/state/zenith-vision/blind-annotation/normal-v1"
items = []
matched = expected = 0
weighted_iou = 0.0
by_kind: dict[str, dict[str, float | int]] = {}
for document in sorted(root.glob("*.ora")):
    boxes = extract_blind_boxes(document)
    labels = tuple(RegionLabel(kind, box) for kind, box in boxes.items())
    metrics = evaluate_regions(propose_profile_regions(1920, 1080, ui_scale="normal"), labels)
    matched += metrics.matched
    expected += metrics.expected
    weighted_iou += metrics.mean_iou * metrics.expected
    items.append({"item_id": document.stem, "labels": {
        kind: [box.x, box.y, box.width, box.height] for kind, box in boxes.items()
    }})
    for label in labels:
        kind_metrics = evaluate_regions(
            propose_profile_regions(1920, 1080, ui_scale="normal"), (label,),
        )
        row = by_kind.setdefault(label.kind, {"labels": 0, "matched": 0, "iou_sum": 0.0})
        row["labels"] += 1
        row["matched"] += kind_metrics.matched
        row["iou_sum"] += kind_metrics.mean_iou
result = {
    "format": "zenith-vision.blind-annotation-result", "version": 1,
    "profile": "normal", "method": "freehand_krita_rectangles",
    "items": items, "metrics": {
        "labels": expected, "matched": matched,
        "mean_iou": round(weighted_iou / expected, 6),
        "recall_at_50": round(matched / expected, 6),
        "by_kind": {
            kind: {"labels": row["labels"], "matched": row["matched"],
                   "mean_iou": round(float(row["iou_sum"]) / int(row["labels"]), 6)}
            for kind, row in sorted(by_kind.items())
        },
    },
}
destination = root / "result.json"
temporary = destination.with_name(".result.json.tmp")
temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
os.replace(temporary, destination)
print(json.dumps(result["metrics"], separators=(",", ":")))
