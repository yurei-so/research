from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

from zenith_vision.holdout_contract import resolve_holdout_directories
from zenith_vision.model_bundle import digest_panel_corpus, load_model_bundle, region_plan_digest
from zenith_vision.panel_regions import crop_panel_regions, panel_region_plan


CLASSES = ("hero", "inventory")
STATE = Path.home() / ".local/state/zenith-vision/panel-batches"


def expected_plan() -> list[dict[str, object]]:
    return [{"id": item.region_id, "evidence": item.evidence, "tile": item.tile,
             "box": list(item.box)} for item in panel_region_plan()]


def build_backbone(device: torch.device) -> nn.Module:
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    return nn.Sequential(model.features, model.avgpool, nn.Flatten()).eval().to(device)


def evaluate() -> dict[str, object]:
    model_path_value = os.environ.get("ZENITH_LOCALIZED_MODEL")
    if not model_path_value:
        raise RuntimeError("ZENITH_LOCALIZED_MODEL is required")
    holdout_names = os.environ.get("ZENITH_HOLDOUT_SEGMENTS")
    if not holdout_names:
        raise RuntimeError("ZENITH_HOLDOUT_SEGMENTS is required")
    holdouts = resolve_holdout_directories(STATE, holdout_names)
    model_path = Path(model_path_value).resolve()
    allowed = (Path.home() / ".local/state/zenith-vision/models/localized-panel").resolve()
    if model_path.parent != allowed or model_path.is_symlink():
        raise RuntimeError("localized model path is outside the approved model directory")
    bundle, model_sha256 = load_model_bundle(model_path)
    plan = expected_plan()
    if region_plan_digest(plan) != bundle["region_plan_sha256"]:
        raise RuntimeError("runtime region plan differs from candidate")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    backbone = build_backbone(device)
    transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    heads = {}
    for kind in CLASSES:
        value = bundle["heads"][kind]
        weight = torch.tensor(value["weight"], dtype=torch.float32, device=device)
        bias = torch.tensor(float(value["bias"]), dtype=torch.float32, device=device)
        heads[kind] = (weight, bias)

    exact = 0
    total = 0
    per_class = {kind: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for kind in CLASSES}
    states: dict[str, dict[str, int]] = {}
    threshold = float(bundle["threshold"])
    with torch.inference_mode():
        for directory in holdouts:
            labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
            for row in labels["items"]:
                actual_panels = set(row["panels"])
                state = "+".join(sorted(actual_panels)) or "closed"
                states.setdefault(state, {"count": 0, "exact": 0})
                calls = []
                with Image.open(directory / f"{row['id']}-left.png") as left, Image.open(
                    directory / f"{row['id']}-center.png"
                ) as center:
                    for kind in CLASSES:
                        proposals = crop_panel_regions(left, center, evidence=kind)
                        try:
                            inputs = torch.stack([transform(crop.convert("RGB")) for _, crop in proposals]).to(device)
                            embeddings = backbone(inputs)
                            weight, bias = heads[kind]
                            probability = torch.sigmoid(embeddings @ weight + bias).max().item()
                            calls.append(probability >= threshold)
                        finally:
                            for _, crop in proposals:
                                crop.close()
                actual = [kind in actual_panels for kind in CLASSES]
                matched = calls == actual
                exact += matched; total += 1
                states[state]["count"] += 1; states[state]["exact"] += matched
                for index, kind in enumerate(CLASSES):
                    called, expected = calls[index], actual[index]
                    key = "tp" if called and expected else "fp" if called else "fn" if expected else "tn"
                    per_class[kind][key] += 1
    state_accuracy = {kind: value["exact"] / value["count"] for kind, value in states.items()}
    class_error_rates = {kind: (value["fp"] + value["fn"]) / total for kind, value in per_class.items()}
    passed = exact / total >= 0.875 and min(state_accuracy.values()) >= 0.75
    passed = passed and all(value <= 0.125 for value in class_error_rates.values())
    return {
        "experiment": "panel-localized-holdout-v2", "device": device.type, "holdout_used": True,
        "training_performed": False, "threshold": threshold, "model_sha256": model_sha256,
        "holdout_sha256": digest_panel_corpus(holdouts), "count": total, "exact": exact,
        "exact_accuracy": exact / total, "states": states, "state_accuracy": state_accuracy,
        "per_class": per_class, "class_error_rates": class_error_rates,
        "promotion_gate": {"passed": passed, "requirements": {
            "aggregate_exact_accuracy": 0.875, "minimum_state_accuracy": 0.75,
            "maximum_class_error_rate": 0.125,
        }},
    }


print(json.dumps(evaluate(), separators=(",", ":")))
