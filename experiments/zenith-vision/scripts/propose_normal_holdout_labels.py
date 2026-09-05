import json
from pathlib import Path

from zenith_vision import BoundingBox, create_annotation_proposal, create_contact_sheet

dataset = Path.home() / ".local/state/zenith-vision/datasets/operator-normal-holdout-v1"
manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
review = dataset / "annotation-review"
boxes = {
    "objectives": BoundingBox(0.84, 0.0, 0.16, 0.54),
    "skill_bar": BoundingBox(0.30, 0.84, 0.40, 0.16),
    "minimap": BoundingBox(0.81, 0.74, 0.19, 0.26),
}
overlays = []
for item in manifest["items"]:
    overlay, _ = create_annotation_proposal(
        dataset / item["media"], review, item_id=item["id"], boxes=boxes,
    )
    overlays.append((item["id"], overlay))
print(create_contact_sheet(overlays, review / "contact-sheet.png"))
