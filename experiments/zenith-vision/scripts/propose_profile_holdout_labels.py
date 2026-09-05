import argparse
import json
from pathlib import Path

from zenith_vision import BoundingBox, create_annotation_proposal, create_contact_sheet

parser = argparse.ArgumentParser()
parser.add_argument("dataset_name")
parser.add_argument("ui_scale", choices=("normal", "large"))
args = parser.parse_args()
profiles = {
    "normal": {
        "objectives": BoundingBox(0.84, 0.0, 0.16, 0.54),
        "skill_bar": BoundingBox(0.30, 0.84, 0.40, 0.16),
        "minimap": BoundingBox(0.81, 0.74, 0.19, 0.26),
    },
    "large": {
        "objectives": BoundingBox(0.83, 0.0, 0.17, 0.55),
        "skill_bar": BoundingBox(0.30, 0.84, 0.43, 0.16),
        "minimap": BoundingBox(0.79, 0.70, 0.21, 0.30),
    },
}
dataset = Path.home() / ".local/state/zenith-vision/datasets" / args.dataset_name
manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
if manifest.get("ui_scale") != args.ui_scale:
    raise RuntimeError("dataset UI scale does not match the requested annotation profile")
review = dataset / "annotation-review"
overlays = []
for item in manifest["items"]:
    overlay, _ = create_annotation_proposal(
        dataset / item["media"], review, item_id=item["id"], boxes=profiles[args.ui_scale],
    )
    overlays.append((item["id"], overlay))
print(create_contact_sheet(overlays, review / "contact-sheet.png"))
