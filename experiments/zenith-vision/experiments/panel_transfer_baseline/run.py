from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small


SEED = 20260824
CLASSES = ("hero", "inventory")
STATE = Path.home() / ".local/state/zenith-vision/panel-batches"
BATCHES = (
    STATE / "small-world-boss-001",
    STATE / "small-world-boss-002",
    STATE / "small-world-boss-dev-003",
    STATE / "small-ui-inventory-negatives-dev-004",
)


class PanelDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, rows: list[tuple[Path, Path, tuple[float, float]]], *, training: bool) -> None:
        self.rows = rows
        self.training = training
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomAffine(degrees=2, translate=(0.10, 0.06), scale=(0.92, 1.08)) if training else nn.Identity(),
            transforms.ColorJitter(brightness=0.20, contrast=0.20, saturation=0.12) if training else nn.Identity(),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])

    def __len__(self) -> int:
        return len(self.rows) * (8 if self.training else 1)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        left_path, center_path, labels = self.rows[index % len(self.rows)]
        with Image.open(left_path) as left, Image.open(center_path) as center:
            canvas = Image.new("RGB", (448, 224), "black")
            canvas.paste(left.convert("RGB").resize((224, 224)), (0, 0))
            canvas.paste(center.convert("RGB").resize((224, 224)), (224, 0))
        return self.transform(canvas), torch.tensor(labels, dtype=torch.float32)


def load_batch(directory: Path) -> list[tuple[Path, Path, tuple[float, float]]]:
    payload = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
    rows = []
    for item in payload["items"]:
        panels = set(item["panels"])
        rows.append((directory / f"{item['id']}-left.png", directory / f"{item['id']}-center.png",
                     tuple(float(kind in panels) for kind in CLASSES)))
    return rows


def build_model(device: torch.device) -> nn.Module:
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    for parameter in model.parameters():
        parameter.requires_grad = False
    final = model.classifier[-1]
    model.classifier[-1] = nn.Linear(final.in_features, len(CLASSES))
    for parameter in model.classifier.parameters():
        parameter.requires_grad = True
    return model.to(device)


def run_fold(train_rows: list, test_rows: list, device: torch.device) -> dict[str, object]:
    model = build_model(device)
    train_loader = DataLoader(PanelDataset(train_rows, training=True), batch_size=16, shuffle=True,
                              num_workers=0, generator=torch.Generator().manual_seed(SEED))
    test_loader = DataLoader(PanelDataset(test_rows, training=False), batch_size=16, shuffle=False, num_workers=0)
    positives = torch.tensor(np.asarray([row[2] for row in train_rows]).sum(axis=0), device=device)
    negatives = len(train_rows) - positives
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.clamp(negatives / positives, min=0.5, max=4.0))
    optimizer = torch.optim.AdamW(model.classifier.parameters(), lr=8e-4, weight_decay=1e-3)
    model.train()
    for _ in range(18):
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(inputs), targets)
            loss.backward()
            optimizer.step()
    model.eval()
    exact = 0
    per_class = {kind: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for kind in CLASSES}
    with torch.inference_mode():
        for inputs, targets in test_loader:
            calls = torch.sigmoid(model(inputs.to(device))).cpu() >= 0.5
            actual = targets >= 0.5
            exact += int((calls == actual).all(dim=1).sum())
            for index, kind in enumerate(CLASSES):
                for called, expected in zip(calls[:, index], actual[:, index], strict=True):
                    key = "tp" if called and expected else "fp" if called else "fn" if expected else "tn"
                    per_class[kind][key] += 1
    return {"count": len(test_rows), "exact": exact, "exact_accuracy": exact / len(test_rows),
            "per_class": per_class}


def main() -> None:
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batches = [load_batch(path) for path in BATCHES]
    folds = []
    for held in range(len(batches)):
        training = [row for index, batch in enumerate(batches) if index != held for row in batch]
        folds.append({"held_batch": held + 1, **run_fold(training, batches[held], device)})
    print(json.dumps({"experiment": "panel-transfer-baseline-v2", "device": device.type,
                      "backbone": "mobilenet_v3_small_frozen", "holdout_used": False,
                      "folds": folds}, separators=(",", ":")))


main()
