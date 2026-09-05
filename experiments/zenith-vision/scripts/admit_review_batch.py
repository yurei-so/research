import argparse
from pathlib import Path

from zenith_vision import admit_review_batch

parser = argparse.ArgumentParser()
parser.add_argument("batch_id")
parser.add_argument("dataset_name")
parser.add_argument("--ui-scale", choices=("small", "normal", "large", "larger"))
args = parser.parse_args()
state = Path.home() / ".local/state/zenith-vision"
manifest = admit_review_batch(
    state / "review-batches" / args.batch_id,
    state / "datasets" / args.dataset_name,
    dataset_name=args.dataset_name,
    ui_scale=args.ui_scale,
)
print(manifest)
