#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
import argparse
import json
from pathlib import Path

from dataset_contract import validate_manifest, validate_shard_arrays

parser = argparse.ArgumentParser()
parser.add_argument("manifest", type=Path)
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
summary = validate_manifest(manifest, args.manifest.parent)
import numpy as np
content = []
for shard in manifest["shards"]:
    with np.load(args.manifest.parent / shard["path"], allow_pickle=False) as loaded:
        content.append(validate_shard_arrays({name: loaded[name] for name in loaded.files}, shard["scene_seed"]))
summary["content"] = {
    "minimum_image_std": min(item["image_std"] for item in content),
    "minimum_depth": min(item["minimum_depth"] for item in content),
    "maximum_depth": max(item["maximum_depth"] for item in content),
    "mean_edge_fraction": sum(item["edge_fraction"] for item in content) / len(content),
}
print(json.dumps(summary, sort_keys=True))
