from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image


PANEL_CLASSES = ("hero", "inventory")


@dataclass(frozen=True)
class LabeledPanelSample:
    sample_id: str
    features: np.ndarray
    panels: frozenset[str]


@dataclass(frozen=True)
class RidgePanelModel:
    feature_mean: np.ndarray
    feature_scale: np.ndarray
    weights: np.ndarray
    classes: tuple[str, ...] = PANEL_CLASSES

    def scores(self, features: np.ndarray) -> dict[str, float]:
        normalized = (features - self.feature_mean) / self.feature_scale
        vector = np.append(normalized, 1.0)
        raw = vector @ self.weights
        return {kind: float(np.clip(score, 0.0, 1.0)) for kind, score in zip(self.classes, raw, strict=True)}

    def predict(self, features: np.ndarray, *, threshold: float = 0.5) -> frozenset[str]:
        return frozenset(kind for kind, score in self.scores(features).items() if score >= threshold)


def extract_panel_features(left: Image.Image, center: Image.Image) -> np.ndarray:
    return np.concatenate((_tile_features(left), _tile_features(center)))


def extract_local_panel_features(left: Image.Image, center: Image.Image) -> np.ndarray:
    """Translation-tolerant local structure for movable GW2 panels."""
    return np.concatenate((_local_tile_features(left), _local_tile_features(center)))


def load_labeled_panel_batch(
    directory: Path, *, feature_extractor: Callable[[Image.Image, Image.Image], np.ndarray] = extract_panel_features,
) -> tuple[LabeledPanelSample, ...]:
    labels = json.loads((directory / "labels.json").read_text(encoding="utf-8"))
    if labels.get("format") != "zenith-vision.panel-labels" or labels.get("version") != 1:
        raise ValueError("unsupported panel labels")
    samples: list[LabeledPanelSample] = []
    for row in labels.get("items", []):
        sample_id = row["id"]
        panels = frozenset(row["panels"])
        if not panels.issubset(PANEL_CLASSES):
            raise ValueError("unsupported panel label")
        with Image.open(directory / f"{sample_id}-left.png") as left, Image.open(
            directory / f"{sample_id}-center.png"
        ) as center:
            features = feature_extractor(left, center)
        samples.append(LabeledPanelSample(sample_id, features, panels))
    if not samples:
        raise ValueError("panel label set is empty")
    return tuple(samples)


def train_ridge_panel_model(
    samples: tuple[LabeledPanelSample, ...], *, regularization: float = 2.0,
) -> RidgePanelModel:
    if len(samples) < 4:
        raise ValueError("at least four labeled samples are required")
    if regularization <= 0:
        raise ValueError("regularization must be positive")
    x = np.stack([sample.features for sample in samples])
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-6] = 1.0
    normalized = (x - mean) / scale
    design = np.column_stack((normalized, np.ones(len(samples))))
    targets = np.asarray([[float(kind in sample.panels) for kind in PANEL_CLASSES] for sample in samples])
    penalty = np.eye(design.shape[1]) * regularization
    penalty[-1, -1] = 0.0
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
    return RidgePanelModel(mean, scale, weights)


def evaluate_panel_model(
    model: RidgePanelModel, samples: tuple[LabeledPanelSample, ...], *, threshold: float = 0.5,
) -> dict[str, object]:
    exact = 0
    per_class: dict[str, dict[str, int]] = {kind: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for kind in PANEL_CLASSES}
    rows: list[dict[str, object]] = []
    for sample in samples:
        predicted = model.predict(sample.features, threshold=threshold)
        exact += predicted == sample.panels
        for kind in PANEL_CLASSES:
            actual, called = kind in sample.panels, kind in predicted
            key = "tp" if actual and called else "fp" if called else "fn" if actual else "tn"
            per_class[kind][key] += 1
        rows.append({"id": sample.sample_id, "actual": sorted(sample.panels),
                     "predicted": sorted(predicted), "scores": model.scores(sample.features)})
    return {"sample_count": len(samples), "exact_matches": exact,
            "exact_accuracy": exact / len(samples), "per_class": per_class, "rows": rows}


def _tile_features(image: Image.Image) -> np.ndarray:
    gray = np.asarray(image.convert("L").resize((64, 48), Image.Resampling.BILINEAR), dtype=np.float64) / 255.0
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    channels = np.stack((gray, gx, gy), axis=-1)
    pooled: list[float] = []
    for row in range(6):
        for column in range(8):
            cell = channels[row * 8:(row + 1) * 8, column * 8:(column + 1) * 8]
            pooled.extend(cell.mean(axis=(0, 1)))
            pooled.append(float(cell[:, :, 0].std()))
    hist, _ = np.histogram(gray, bins=16, range=(0.0, 1.0), density=True)
    return np.asarray(pooled + list(hist / hist.sum()), dtype=np.float64)


def _local_tile_features(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB").resize((128, 96), Image.Resampling.BILINEAR), dtype=np.float64) / 255.0
    gray = rgb.mean(axis=2)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edge = gx + gy
    cells: list[list[float]] = []
    for row in range(12):
        for column in range(16):
            ys, xs = slice(row * 8, (row + 1) * 8), slice(column * 8, (column + 1) * 8)
            cell_gray, cell_edge, cell_saturation = gray[ys, xs], edge[ys, xs], saturation[ys, xs]
            cells.append([float(cell_gray.mean()), float(cell_gray.std()),
                          float(cell_edge.mean()), float(cell_saturation.mean())])
    matrix = np.asarray(cells)
    translation_invariant = np.concatenate([np.sort(matrix[:, index]) for index in range(matrix.shape[1])])
    histograms = np.concatenate([
        np.histogram(matrix[:, index], bins=16, range=(0.0, 1.0), density=False)[0] / len(matrix)
        for index in range(matrix.shape[1])
    ])
    coarse: list[float] = []
    grid = matrix.reshape(12, 16, 4)
    for row in range(3):
        for column in range(4):
            coarse.extend(grid[row * 4:(row + 1) * 4, column * 4:(column + 1) * 4].mean(axis=(0, 1)))
    return np.concatenate((translation_invariant, histograms, np.asarray(coarse)))
