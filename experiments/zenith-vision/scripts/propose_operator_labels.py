from pathlib import Path

from zenith_vision import BoundingBox, create_annotation_proposal

dataset = Path.home() / ".local/state/zenith-vision/datasets/operator-pilot-v1"
overlay, proposal = create_annotation_proposal(
    dataset / "media/operator-00001.png",
    dataset / "annotation-review",
    item_id="operator-00001",
    boxes={
        "objectives": BoundingBox(0.855, 0.0, 0.145, 0.36),
        "skill_bar": BoundingBox(0.349, 0.877, 0.379, 0.123),
        "minimap": BoundingBox(0.831, 0.771, 0.169, 0.228),
    },
)
print(overlay)
print(proposal)
