import argparse
import json
from pathlib import Path

from PIL import Image

from zenith_vision import BoundingBox, DatasetManifest, RegionLabel, evaluate_regions, propose_default_regions, propose_profile_regions

parser = argparse.ArgumentParser()
parser.add_argument("dataset_name")
parser.add_argument("--ui-scale", choices=("small", "normal", "large"))
args = parser.parse_args()
dataset = Path.home() / ".local/state/zenith-vision/datasets" / args.dataset_name
manifest = DatasetManifest.load(dataset / "manifest.json")
matched = expected = proposed = 0
weighted_iou = 0.0
by_kind: dict[str, dict[str, float | int]] = {}
for item in manifest.items:
    if item.labels_path is None:
        raise RuntimeError(f"{item.item_id}: labels are not approved")
    raw = json.loads(Path(item.labels_path).read_text(encoding="utf-8"))
    labels = tuple(RegionLabel(row["kind"], BoundingBox(*row["box"])) for row in raw["regions"])
    with Image.open(item.media_path) as image:
        proposals_for_item = (
            propose_profile_regions(*image.size, ui_scale=args.ui_scale)
            if args.ui_scale else propose_default_regions(*image.size)
        )
    metrics = evaluate_regions(proposals_for_item, labels)
    matched += metrics.matched
    expected += metrics.expected
    proposed += metrics.proposed
    weighted_iou += metrics.mean_iou * metrics.expected
    for label in labels:
        kind_metrics = evaluate_regions(
            proposals_for_item, (label,),
        )
        row = by_kind.setdefault(label.kind, {"labels": 0, "matched": 0, "iou_sum": 0.0})
        row["labels"] += 1
        row["matched"] += kind_metrics.matched
        row["iou_sum"] += kind_metrics.mean_iou
kind_results = {
    kind: {
        "labels": row["labels"], "matched": row["matched"],
        "mean_iou": round(float(row["iou_sum"]) / int(row["labels"]), 6),
        "recall_at_50": round(int(row["matched"]) / int(row["labels"]), 6),
    }
    for kind, row in sorted(by_kind.items())
}
result = {
    "format": "zenith-vision.holdout-result", "version": 1,
    "dataset": manifest.name, "items": len(manifest.items),
    "profile": args.ui_scale or "generic_default",
    "labels": expected, "matched": matched, "proposals_evaluated": proposed,
    "mean_iou": round(weighted_iou / expected, 6),
    "recall_at_50": round(matched / expected, 6),
    "by_kind": kind_results,
}
print(json.dumps(result, separators=(",", ":")))
