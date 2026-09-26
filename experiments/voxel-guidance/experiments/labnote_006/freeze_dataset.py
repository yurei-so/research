#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dataset_contract import SPLIT_RANGES, canonical_json, sha256_file, validate_manifest, validate_shard_arrays


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and freeze the VG-006 dataset set.")
    parser.add_argument("dataset_root", type=Path)
    parser.add_argument("--blender-version", required=True)
    args = parser.parse_args()

    root = args.dataset_root.resolve()
    split_records = []
    all_seeds: set[int] = set()
    import numpy as np

    for split in ("train", "validation", "test"):
        manifest_path = root / split / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary = validate_manifest(manifest, manifest_path.parent)
        expected = set(SPLIT_RANGES[split])
        actual = set(summary["scene_seeds"])
        if actual != expected:
            raise ValueError(f"{split} does not contain its exact frozen seed range")
        if all_seeds & actual:
            raise ValueError("dataset splits overlap")
        all_seeds |= actual
        for shard in manifest["shards"]:
            with np.load(manifest_path.parent / shard["path"], allow_pickle=False) as loaded:
                validate_shard_arrays({name: loaded[name] for name in loaded.files}, shard["scene_seed"])
        split_records.append({
            "split": split,
            "manifest": f"{split}/manifest.json",
            "manifest_sha256": sha256_file(manifest_path),
            "shards": summary["shards"],
            "seed_first": min(actual),
            "seed_last": max(actual),
        })

    frozen = {
        "format": "voxel-guidance.synthetic-spatial-dataset-set",
        "version": 1,
        "blender_version": args.blender_version,
        "sequences": len(all_seeds),
        "frames_per_sequence": 4,
        "splits": split_records,
    }
    destination = root / "dataset-manifest.json"
    encoded = canonical_json(frozen) + "\n"
    if destination.exists() and destination.read_text(encoding="utf-8") != encoded:
        raise ValueError("refusing to overwrite a different frozen dataset manifest")
    destination.write_text(encoded, encoding="utf-8")
    print(json.dumps({"manifest": str(destination), "sha256": sha256_file(destination), **frozen}, sort_keys=True))


if __name__ == "__main__":
    main()
