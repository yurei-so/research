from pathlib import Path

from zenith_vision import approve_annotation_proposal

dataset = Path.home() / ".local/state/zenith-vision/datasets/operator-pilot-v1"
labels = approve_annotation_proposal(
    dataset,
    dataset / "annotation-review/operator-00001-proposal.json",
    item_id="operator-00001",
)
print(labels)
