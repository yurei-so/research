from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from zenith_vision.model_bundle import digest_panel_corpus, region_plan_digest, write_model_bundle
from zenith_vision.panel_regions import crop_panel_regions
from zenith_vision.panel_regions import panel_region_plan


SEED = 20260825
CLASSES = ("hero", "inventory")
THRESHOLD = 0.65
STATE = Path.home() / ".local/state/zenith-vision/panel-batches"
BATCHES = (
    STATE / "small-world-boss-001",
    STATE / "small-world-boss-002",
    STATE / "small-world-boss-dev-003",
    STATE / "small-ui-inventory-negatives-dev-004",
    STATE / "small-ui-inventory-position-left-dev-005",
    STATE / "small-ui-inventory-position-right-dev-006",
    STATE / "small-ui-inventory-position-center-dev-007",
    STATE / "small-ui-hero-snowy-hoelbrak-dev-008",
)


@dataclass(frozen=True)
class Sample:
    sample_id: str
    batch: int
    labels: tuple[float, float]
    embeddings: tuple[torch.Tensor, torch.Tensor]


def load_rows() -> list[tuple[str, int, Path, Path, tuple[float, float]]]:
    rows = []
    for batch_index, directory in enumerate(BATCHES):
        payload = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
        for item in payload["items"]:
            panels = set(item["panels"])
            rows.append((item["id"], batch_index, directory / f"{item['id']}-left.png",
                         directory / f"{item['id']}-center.png",
                         tuple(float(kind in panels) for kind in CLASSES)))
    return rows


def build_backbone(device: torch.device) -> nn.Module:
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    return nn.Sequential(model.features, model.avgpool, nn.Flatten()).eval().to(device)


def embed_rows(device: torch.device) -> list[Sample]:
    backbone = build_backbone(device)
    transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    samples = []
    with torch.inference_mode():
        for sample_id, batch, left_path, center_path, labels in load_rows():
            class_embeddings = []
            with Image.open(left_path) as left, Image.open(center_path) as center:
                for kind in CLASSES:
                    proposals = crop_panel_regions(left, center, evidence=kind)
                    try:
                        inputs = torch.stack([transform(crop.convert("RGB")) for _, crop in proposals]).to(device)
                        class_embeddings.append(backbone(inputs).cpu())
                    finally:
                        for _, crop in proposals:
                            crop.close()
            samples.append(Sample(sample_id, batch, labels, tuple(class_embeddings)))
    return samples


def train_head(samples: list[Sample], class_index: int, device: torch.device) -> nn.Linear:
    width = samples[0].embeddings[class_index].shape[1]
    head = nn.Linear(width, 1).to(device)
    labels = torch.tensor([sample.labels[class_index] for sample in samples], device=device)
    positives = labels.sum().clamp(min=1)
    negatives = (len(samples) - labels.sum()).clamp(min=1)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=(negatives / positives).reshape(1))
    optimizer = torch.optim.AdamW(head.parameters(), lr=2e-3, weight_decay=2e-3)
    bags = [sample.embeddings[class_index].to(device) for sample in samples]
    for _ in range(400):
        logits = []
        for regions in bags:
            region_logits = head(regions).flatten()
            # Normalized smooth maximum avoids a proposal-count-dependent
            # offset while keeping gradients across plausible local regions.
            logits.append(torch.logsumexp(region_logits * 4.0, dim=0) / 4.0
                          - np.log(len(region_logits)) / 4.0)
        loss = loss_fn(torch.stack(logits), labels)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
    return head


def score(head: nn.Linear, sample: Sample, class_index: int, device: torch.device) -> tuple[float, int]:
    with torch.inference_mode():
        probabilities = torch.sigmoid(head(sample.embeddings[class_index].to(device)).flatten())
    value, region = probabilities.max(dim=0)
    return float(value), int(region)


def run_fold(samples: list[Sample], held_batch: int, device: torch.device) -> dict[str, object]:
    training = [sample for sample in samples if sample.batch != held_batch]
    testing = [sample for sample in samples if sample.batch == held_batch]
    heads = [train_head(training, index, device) for index in range(len(CLASSES))]
    exact = 0
    per_class = {kind: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for kind in CLASSES}
    winners = {kind: {} for kind in CLASSES}
    for sample in testing:
        scores = [score(head, sample, index, device) for index, head in enumerate(heads)]
        calls = [value >= THRESHOLD for value, _ in scores]
        actual = [bool(value) for value in sample.labels]
        exact += calls == actual
        for index, kind in enumerate(CLASSES):
            called, expected = calls[index], actual[index]
            key = "tp" if called and expected else "fp" if called else "fn" if expected else "tn"
            per_class[kind][key] += 1
            region = str(scores[index][1])
            winners[kind][region] = winners[kind].get(region, 0) + 1
    return {"count": len(testing), "exact": exact, "exact_accuracy": exact / len(testing),
            "per_class": per_class, "winning_region_counts": winners}


def promotion_gate(folds: list[dict[str, object]]) -> dict[str, object]:
    total = sum(int(fold["count"]) for fold in folds)
    exact = sum(int(fold["exact"]) for fold in folds)
    class_errors = {}
    for kind in CLASSES:
        errors = sum(int(fold["per_class"][kind][key]) for fold in folds for key in ("fp", "fn"))
        class_errors[kind] = errors / total
    passed = exact / total >= 0.80 and min(float(fold["exact_accuracy"]) for fold in folds) >= 0.70
    passed = passed and all(rate <= 0.20 for rate in class_errors.values())
    return {"passed": passed, "aggregate_exact": exact, "aggregate_count": total,
            "aggregate_exact_accuracy": exact / total, "class_error_rates": class_errors,
            "requirements": {"aggregate_exact_accuracy": 0.80, "minimum_fold_accuracy": 0.70,
                             "maximum_class_error_rate": 0.20}}


def package_candidate(samples: list[Sample], device: torch.device) -> dict[str, object]:
    heads = [train_head(samples, index, device) for index in range(len(CLASSES))]
    plan = [{"id": item.region_id, "evidence": item.evidence, "tile": item.tile,
             "box": list(item.box)} for item in panel_region_plan()]
    payload = {
        "format": "zenith-vision.localized-panel-model", "version": 1,
        "architecture": "mobilenet_v3_small_frozen_mil_linear_heads",
        "backbone_weights": "MobileNet_V3_Small_Weights.DEFAULT",
        "classes": list(CLASSES), "threshold": THRESHOLD,
        "corpus_sha256": digest_panel_corpus(BATCHES),
        "region_plan": plan, "region_plan_sha256": region_plan_digest(plan),
        "heads": {
            kind: {"weight": heads[index].weight.detach().cpu().flatten().tolist(),
                   "bias": float(heads[index].bias.detach().cpu().item())}
            for index, kind in enumerate(CLASSES)
        },
    }
    path, sha256 = write_model_bundle(
        Path.home() / ".local/state/zenith-vision/models/localized-panel", payload,
    )
    return {"format": payload["format"], "version": payload["version"],
            "sha256": sha256, "file": path.name, "corpus_sha256": payload["corpus_sha256"],
            "region_plan_sha256": payload["region_plan_sha256"]}


def main() -> None:
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    samples = embed_rows(device)
    folds = [run_fold(samples, held, device) for held in range(len(BATCHES))]
    gate = promotion_gate(folds)
    candidate = package_candidate(samples, device) if gate["passed"] else None
    print(json.dumps({"experiment": "panel-localized-transfer-v4", "device": device.type,
                      "backbone": "mobilenet_v3_small_frozen", "threshold": THRESHOLD,
                      "holdout_used": False, "folds": folds, "promotion_gate": gate,
                      "candidate": candidate},
                     separators=(",", ":")))


main()
