import json
from pathlib import Path

from zenith_vision import BoundingBox, create_annotation_proposal, create_contact_sheet

dataset = Path.home() / ".local/state/zenith-vision/datasets/operator-holdout-v1"
manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
review = dataset / "annotation-review"
boxes = {
    "objectives": BoundingBox(0.855, 0.0, 0.145, 0.36),
    "skill_bar": BoundingBox(0.349, 0.877, 0.379, 0.123),
    "minimap": BoundingBox(0.831, 0.771, 0.169, 0.228),
}
overlays = []
for item in manifest["items"]:
    overlay, _ = create_annotation_proposal(
        dataset / item["media"], review, item_id=item["id"], boxes=boxes,
    )
    overlays.append((item["id"], overlay))
sheet = create_contact_sheet(overlays, review / "contact-sheet.png")
print(sheet)
