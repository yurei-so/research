import argparse
from pathlib import Path

from zenith_vision import approve_annotation_batch

parser = argparse.ArgumentParser()
parser.add_argument("dataset_name")
args = parser.parse_args()
dataset = Path.home() / ".local/state/zenith-vision/datasets" / args.dataset_name
labels = approve_annotation_batch(dataset, dataset / "annotation-review")
print(f"approved {len(labels)} annotation sets")
