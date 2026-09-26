#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import argparse
import json
import os
import random
import time
from pathlib import Path

import numpy as np

from dataset_contract import canonical_json, sha256_file, validate_manifest, validate_shard_arrays


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--max-train", type=int)
    parser.add_argument("--max-validation", type=int)
    parser.add_argument("--max-test", type=int)
    return parser.parse_args()


def load_split(root: Path, split: str, maximum: int | None):
    manifest_path = root / split / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, manifest_path.parent)
    rows = []
    selected_shards = manifest["shards"][:maximum] if maximum is not None else manifest["shards"]
    for shard in selected_shards:
        with np.load(manifest_path.parent / shard["path"], allow_pickle=False) as loaded:
            validate_shard_arrays({name: loaded[name] for name in loaded.files}, shard["scene_seed"])
            rows.append({name: loaded[name].copy() for name in ("image", "depth", "edge", "ego")})
    return rows, sha256_file(manifest_path)


def metrics(predicted_depth, predicted_edge, depth, edge):
    import torch
    depth_mae = torch.mean(torch.abs(predicted_depth - depth)).item()
    free_pred, free_true = predicted_depth >= 5.0, depth >= 5.0
    intersection = torch.logical_and(free_pred, free_true).sum().item()
    union = torch.logical_or(free_pred, free_true).sum().item()
    edge_pred, edge_true = predicted_edge.sigmoid() >= 0.5, edge >= 0.5
    tp = torch.logical_and(edge_pred, edge_true).sum().item()
    fp = torch.logical_and(edge_pred, ~edge_true).sum().item()
    fn = torch.logical_and(~edge_pred, edge_true).sum().item()
    return {"depth_mae_m": depth_mae, "free_space_iou": intersection / max(1, union),
            "discontinuity_f1": 2 * tp / max(1, 2 * tp + fp + fn)}


def tensors(rows, torch):
    images = torch.from_numpy(np.stack([row["image"] for row in rows])).float().div_(255).unsqueeze(2)
    depth = torch.from_numpy(np.stack([row["depth"][-1] for row in rows])).float()
    edge = torch.from_numpy(np.stack([row["edge"][-1] for row in rows])).float()
    ego = torch.from_numpy(np.stack([row["ego"] for row in rows])).float()
    return images, ego, depth, edge


def evaluate(model, batch, device, temporal, torch):
    model.eval()
    images, ego, depth, edge = (item.to(device) for item in batch)
    if not temporal:
        images, ego = images[:, -1:], ego[:, -1:]
    with torch.no_grad():
        predicted_depth, predicted_edge = model(images, ego)
    return metrics(predicted_depth.cpu(), predicted_edge.cpu(), depth.cpu(), edge.cpu())


def train_variant(name, temporal, train, validation, test, args, device, torch):
    from spatial_model import SpatialBeliefModel
    model = SpatialBeliefModel().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    generator = torch.Generator().manual_seed(args.seed)
    train_images, train_ego, train_depth, train_edge = train
    history = []
    start = time.perf_counter()
    for epoch in range(args.epochs):
        model.train()
        order = torch.randperm(len(train_images), generator=generator)
        total = 0.0
        for offset in range(0, len(order), args.batch_size):
            selected = order[offset:offset + args.batch_size]
            images = train_images[selected].to(device)
            ego = train_ego[selected].to(device)
            depth = train_depth[selected].to(device)
            edge = train_edge[selected].to(device)
            if not temporal:
                images, ego = images[:, -1:], ego[:, -1:]
            predicted_depth, predicted_edge = model(images, ego)
            depth_loss = torch.nn.functional.smooth_l1_loss(predicted_depth, depth)
            edge_loss = torch.nn.functional.binary_cross_entropy_with_logits(predicted_edge, edge, pos_weight=torch.tensor(3.0, device=device))
            loss = depth_loss + 0.35 * edge_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            optimizer.step()
            total += loss.item() * len(selected)
        validation_metrics = evaluate(model, validation, device, temporal, torch)
        history.append({"epoch": epoch + 1, "train_loss": total / len(order), "validation": validation_metrics})
        print(json.dumps({"variant": name, **history[-1]}), flush=True)
    test_metrics = evaluate(model, test, device, temporal, torch)
    checkpoint = args.output / f"{name}.pt"
    torch.save({"model": model.state_dict(), "variant": name, "seed": args.seed}, checkpoint)
    return {"variant": name, "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "duration_seconds": time.perf_counter() - start, "history": history,
            "test": test_metrics, "checkpoint": checkpoint.name, "checkpoint_sha256": sha256_file(checkpoint)}


def main():
    args = arguments()
    if not 1 <= args.epochs <= 200 or not 1 <= args.batch_size <= 256:
        raise SystemExit("unsafe training bounds")
    if any(value is not None and value < 1 for value in (args.max_train, args.max_validation, args.max_test)):
        raise SystemExit("unsafe dataset subset bounds")
    args.output.mkdir(parents=True, exist_ok=True)
    os.chmod(args.output, 0o700)
    import torch
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(args.seed)
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device == "auto": device = "cpu"
    if device == "cuda" and not torch.cuda.is_available(): raise SystemExit("CUDA_REQUIRED_BUT_UNAVAILABLE")
    dataset_receipt_path = args.data_root / "dataset-manifest.json"
    dataset_receipt = json.loads(dataset_receipt_path.read_text(encoding="utf-8"))
    if dataset_receipt.get("format") != "voxel-guidance.synthetic-spatial-dataset-set" or dataset_receipt.get("version") != 1:
        raise SystemExit("INVALID_DATASET_SET_MANIFEST")
    expected_digests = {item["split"]: item["manifest_sha256"] for item in dataset_receipt.get("splits", [])}
    loaded, digests = {}, {}
    for split in ("train", "validation", "test"):
        maximum = getattr(args, f"max_{split}")
        rows, digest = load_split(args.data_root, split, maximum)
        if expected_digests.get(split) != digest:
            raise SystemExit(f"FROZEN_{split.upper()}_MANIFEST_MISMATCH")
        loaded[split], digests[split] = tensors(rows, torch), digest
    result = {
        "format": "voxel-guidance.spatial-training-result", "version": 1,
        "seed": args.seed, "device": str(device), "torch": torch.__version__,
        "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "dataset_set_manifest_sha256": sha256_file(dataset_receipt_path),
        "dataset_manifest_sha256": digests, "epochs": args.epochs, "batch_size": args.batch_size,
        "dataset_limits": {"train": args.max_train, "validation": args.max_validation, "test": args.max_test},
        "variants": [],
    }
    result["variants"].append(train_variant("single-frame", False, loaded["train"], loaded["validation"], loaded["test"], args, device, torch))
    result["variants"].append(train_variant("temporal-convgru", True, loaded["train"], loaded["validation"], loaded["test"], args, device, torch))
    single, temporal = (item["test"] for item in result["variants"])
    result["comparison"] = {metric: temporal[metric] - single[metric] for metric in single}
    path = args.output / "result.json"
    path.write_text(canonical_json(result) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "result": str(path), "comparison": result["comparison"]}), flush=True)


if __name__ == "__main__":
    main()
