# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import hashlib
import json
from pathlib import Path

FORMAT = "voxel-guidance.synthetic-spatial-dataset"
VERSION = 1
SPLIT_RANGES = {
    "train": range(1000, 1256),
    "validation": range(2000, 2064),
    "test": range(3000, 3064),
    "calibration": range(9000, 10000),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_manifest(manifest: dict, root: Path, verify_files: bool = True) -> dict:
    if manifest.get("format") != FORMAT or manifest.get("version") != VERSION:
        raise ValueError("unsupported dataset manifest")
    split = manifest.get("split")
    if split not in SPLIT_RANGES:
        raise ValueError("invalid split")
    shards = manifest.get("shards")
    if not isinstance(shards, list) or not shards:
        raise ValueError("manifest has no shards")
    seeds: set[int] = set()
    for shard in shards:
        if set(shard) != {"path", "scene_seed", "sha256", "bytes"}:
            raise ValueError("invalid shard fields")
        seed = shard["scene_seed"]
        if not isinstance(seed, int) or seed not in SPLIT_RANGES[split] or seed in seeds:
            raise ValueError("invalid or duplicate scene seed")
        seeds.add(seed)
        relative = Path(shard["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe shard path")
        path = root / relative
        if verify_files:
            if not path.is_file() or path.stat().st_size != shard["bytes"]:
                raise ValueError(f"missing or changed shard: {relative}")
            if sha256_file(path) != shard["sha256"]:
                raise ValueError(f"digest mismatch: {relative}")
    return {"split": split, "shards": len(shards), "scene_seeds": sorted(seeds)}


def validate_shard_arrays(arrays: dict, expected_seed: int) -> dict:
    import numpy as np
    required = {"image", "depth", "edge", "ego", "scene_seed"}
    if set(arrays) != required:
        raise ValueError("invalid shard arrays")
    image, depth, edge, ego = (arrays[name] for name in ("image", "depth", "edge", "ego"))
    if image.shape != (4, 64, 64) or image.dtype != np.uint8:
        raise ValueError("invalid image tensor")
    if depth.shape != (4, 16, 16) or depth.dtype != np.float32 or not np.isfinite(depth).all():
        raise ValueError("invalid depth tensor")
    if edge.shape != (4, 16, 16) or edge.dtype != np.uint8 or not np.isin(edge, (0, 1)).all():
        raise ValueError("invalid edge tensor")
    if ego.shape != (4, 3) or ego.dtype != np.float32 or not np.isfinite(ego).all():
        raise ValueError("invalid ego-motion tensor")
    if int(arrays["scene_seed"]) != expected_seed:
        raise ValueError("scene seed mismatch")
    if depth.min() < 0 or depth.max() > 20.0 or image.std() < 2.0:
        raise ValueError("degenerate observation or depth")
    recomputed = np.zeros_like(edge)
    recomputed[:, :, 1:] |= np.abs(depth[:, :, 1:] - depth[:, :, :-1]) > 1.0
    recomputed[:, 1:, :] |= np.abs(depth[:, 1:, :] - depth[:, :-1, :]) > 1.0
    if not np.array_equal(edge, recomputed):
        raise ValueError("edge labels do not match depth")
    if not np.allclose(ego[0], 0) or np.linalg.norm(ego[1:, :2], axis=1).min() <= 0:
        raise ValueError("invalid temporal ego-motion")
    return {"image_std": float(image.std()), "minimum_depth": float(depth.min()),
            "maximum_depth": float(depth.max()), "edge_fraction": float(edge.mean())}
