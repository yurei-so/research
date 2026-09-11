from __future__ import annotations

import math
import random
from collections import Counter
from datetime import datetime
from statistics import fmean, pstdev
from typing import Any

from .contract import ContractError, validate_session


TASKS = ("acquire", "construct", "explore", "recover")
HORIZONS = (30, 60, 120, 240, 480)
INVENTORY_CATEGORIES = ("building", "resource", "tool", "food", "other")
BLOCK_CATEGORIES = ("building", "resource", "functional", "other")
FEATURE_GROUPS = {
    "movement": {
        "position_samples_per_minute", "path_distance_per_minute",
        "visited_cells_per_minute", "route_directness", "maximum_radius",
        "vertical_span", "moving_step_fraction",
    },
    "inventory": {
        f"inventory_{direction}_{category}_per_minute"
        for direction in ("gained", "lost") for category in INVENTORY_CATEGORIES
    },
    "block_actions": {
        f"blocks_{action}_{category}_per_minute"
        for action in ("placed", "broken") for category in BLOCK_CATEGORIES
    },
}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _task(task_id: str) -> str:
    task = task_id.rsplit("-", 1)[-1]
    if task not in TASKS:
        raise ContractError("task inference received an unknown task")
    return task


def _block(task_id: str) -> str:
    parts = task_id.split("-")
    if len(parts) != 4 or parts[:2] != ["vg", "block"]:
        raise ContractError("task inference received an invalid scheduled task ID")
    return f"block-{parts[2]}"


def extract_prefix_features(events: Any, horizon_seconds: int) -> dict[str, float]:
    """Return causal behavior features without identity, task, schedule, or markers."""
    if horizon_seconds <= 0:
        raise ContractError("task-inference horizon must be positive")
    checked = validate_session(events)
    start = _time(checked[0]["observed_at"])
    prefix = [event for event in checked
              if (_time(event["observed_at"]) - start).total_seconds() <= horizon_seconds]
    minutes = horizon_seconds / 60

    positions = [event for event in prefix if event["kind"] == "position_sample"]
    path_distance = 0.0
    moving_steps = 0
    comparable_steps = 0
    visited: set[tuple[str, int, int]] = set()
    radii: list[float] = []
    vertical: list[float] = []
    if positions:
        origin = positions[0]["payload"]
        for event in positions:
            point = event["payload"]
            visited.add((point["dimension"], math.floor(point["x"] / 16), math.floor(point["z"] / 16)))
            if point["dimension"] == origin["dimension"]:
                radii.append(math.dist((origin["x"], origin["z"]), (point["x"], point["z"])))
            vertical.append(float(point["y"]))
        for previous, current in zip(positions, positions[1:]):
            a, b = previous["payload"], current["payload"]
            if a["dimension"] != b["dimension"]:
                continue
            distance = math.dist((a["x"], a["z"]), (b["x"], b["z"]))
            # A forced death can teleport the player to spawn. It is apparatus, not behavior.
            if distance > 128:
                continue
            comparable_steps += 1
            path_distance += distance
            moving_steps += distance >= 0.5
    directness = 0.0
    if len(positions) > 1:
        first, last = positions[0]["payload"], positions[-1]["payload"]
        if first["dimension"] == last["dimension"] and path_distance:
            directness = math.dist((first["x"], first["z"]), (last["x"], last["z"])) / path_distance

    inventory_positive = Counter({category: 0 for category in INVENTORY_CATEGORIES})
    inventory_negative = Counter({category: 0 for category in INVENTORY_CATEGORIES})
    block_counts = Counter()
    recovery_window = False
    for event in prefix:
        if event["kind"] == "death":
            recovery_window = True
        elif event["kind"] == "marker" and event["payload"]["marker"] == "recovered":
            recovery_window = False
        elif event["kind"] == "inventory_delta" and not recovery_window:
            delta = event["payload"]["delta"]
            target = inventory_positive if delta > 0 else inventory_negative
            target[event["payload"]["category"]] += abs(delta)
        elif event["kind"] == "block_action":
            payload = event["payload"]
            block_counts[(payload["action"], payload["category"])] += payload["count"]

    result = {
        "position_samples_per_minute": len(positions) / minutes,
        "path_distance_per_minute": path_distance / minutes,
        "visited_cells_per_minute": len(visited) / minutes,
        "route_directness": directness,
        "maximum_radius": max(radii, default=0.0),
        "vertical_span": max(vertical, default=0.0) - min(vertical, default=0.0),
        "moving_step_fraction": moving_steps / comparable_steps if comparable_steps else 0.0,
    }
    for category in INVENTORY_CATEGORIES:
        result[f"inventory_gained_{category}_per_minute"] = inventory_positive[category] / minutes
        result[f"inventory_lost_{category}_per_minute"] = inventory_negative[category] / minutes
    for action in ("placed", "broken"):
        for category in BLOCK_CATEGORIES:
            result[f"blocks_{action}_{category}_per_minute"] = block_counts[(action, category)] / minutes
    return result


def _prepare_folds(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    folds = []
    names = sorted(rows[0]["features"])
    for held_block in sorted({row["block"] for row in rows}):
        train = [row for row in rows if row["block"] != held_block]
        test = [row for row in rows if row["block"] == held_block]
        columns = {name: [row["features"][name] for row in train] for name in names}
        means = {name: fmean(values) for name, values in columns.items()}
        scales = {name: pstdev(values) or 1.0 for name, values in columns.items()}

        def standardized(row: dict[str, Any]) -> list[float]:
            return [(row["features"][name] - means[name]) / scales[name] for name in names]

        folds.append({
            "train": {row["key"]: standardized(row) for row in train},
            "test": {row["key"]: standardized(row) for row in test},
        })
    return folds


def _predict(train: dict[str, list[float]], point: list[float], labels: dict[str, str]) -> str:
    centroids = {}
    for task in TASKS:
        members = [values for key, values in train.items() if labels[key] == task]
        if not members:
            raise ContractError("every training fold must contain every task")
        centroids[task] = [fmean(values) for values in zip(*members)]
    distances = {task: fmean((value - center) ** 2 for value, center in zip(point, centroid))
                 for task, centroid in centroids.items()}
    return min(TASKS, key=lambda task: (distances[task], task))


def _score(folds: list[dict[str, Any]], labels: dict[str, str]) -> dict[str, Any]:
    predictions = []
    for fold in folds:
        for key, point in fold["test"].items():
            predictions.append((labels[key], _predict(fold["train"], point, labels)))
    confusion = {actual: {predicted: 0 for predicted in TASKS} for actual in TASKS}
    for actual, predicted in predictions:
        confusion[actual][predicted] += 1
    f1 = []
    for task in TASKS:
        true_positive = confusion[task][task]
        false_positive = sum(confusion[actual][task] for actual in TASKS if actual != task)
        false_negative = sum(confusion[task][predicted] for predicted in TASKS if predicted != task)
        denominator = 2 * true_positive + false_positive + false_negative
        f1.append(2 * true_positive / denominator if denominator else 0.0)
    return {
        "accuracy": sum(actual == predicted for actual, predicted in predictions) / len(predictions),
        "macro_f1": fmean(f1),
        "confusion": confusion,
    }


def evaluate_task_inference(sessions: Any, *, horizons: tuple[int, ...] = HORIZONS,
                            permutation_samples: int = 10000, seed: int = 1701) -> dict[str, Any]:
    if not isinstance(sessions, list) or len(sessions) != 12:
        raise ContractError("task inference requires the complete 12-session matrix")
    checked = [validate_session(events) for events in sessions]
    identities = [events[0]["task_id"] for events in checked]
    if len(set(identities)) != 12:
        raise ContractError("task inference requires 12 unique scheduled tasks")
    results = {}
    rng = random.Random(seed)
    for horizon in horizons:
        rows = [{"key": events[0]["task_id"], "block": _block(events[0]["task_id"]),
                 "features": extract_prefix_features(events, horizon)} for events in checked]
        labels = {row["key"]: _task(row["key"]) for row in rows}
        folds = _prepare_folds(rows)
        observed = _score(folds, labels)
        null_accuracies = []
        for _ in range(permutation_samples):
            shuffled = dict(labels)
            for block in sorted({row["block"] for row in rows}):
                keys = [row["key"] for row in rows if row["block"] == block]
                values = [shuffled[key] for key in keys]
                rng.shuffle(values)
                shuffled.update(zip(keys, values))
            null_accuracies.append(_score(folds, shuffled)["accuracy"])
        observed["permutation_p_value"] = ((sum(value >= observed["accuracy"] for value in null_accuracies) + 1)
                                             / (permutation_samples + 1))
        observed["chance_accuracy"] = 0.25
        results[str(horizon)] = observed
    return {
        "format": "voxel-guidance.task-inference",
        "version": 1,
        "session_count": 12,
        "block_count": 3,
        "classifier": "z-scored nearest task centroid",
        "validation": "leave-one-seed-block-out",
        "feature_boundary": "causal behavior only; task, schedule, markers, forced death, and recovery inventory churn excluded",
        "horizons_seconds": list(horizons),
        "permutation_samples": permutation_samples,
        "multiple_testing": {
            "method": "Bonferroni",
            "family_size": len(horizons),
            "family_alpha": 0.05,
            "per_horizon_alpha": 0.05 / len(horizons),
        },
        "results": results,
    }


def evaluate_feature_ablation(sessions: Any, *, horizon_seconds: int = 120,
                              permutation_samples: int = 10000, seed: int = 1701) -> dict[str, Any]:
    if not isinstance(sessions, list) or len(sessions) != 12:
        raise ContractError("task inference requires the complete 12-session matrix")
    checked = [validate_session(events) for events in sessions]
    base_rows = [{"key": events[0]["task_id"], "block": _block(events[0]["task_id"]),
                  "features": extract_prefix_features(events, horizon_seconds)} for events in checked]
    labels = {row["key"]: _task(row["key"]) for row in base_rows}
    if len(labels) != 12:
        raise ContractError("task inference requires 12 unique scheduled tasks")
    all_features = set(base_rows[0]["features"])
    variants = {
        "all": all_features,
        "movement_only": FEATURE_GROUPS["movement"],
        "inventory_only": FEATURE_GROUPS["inventory"],
        "block_actions_only": FEATURE_GROUPS["block_actions"],
        "without_movement": all_features - FEATURE_GROUPS["movement"],
        "without_inventory": all_features - FEATURE_GROUPS["inventory"],
        "without_block_actions": all_features - FEATURE_GROUPS["block_actions"],
    }
    rng = random.Random(seed)
    permutations = []
    for _ in range(permutation_samples):
        shuffled = dict(labels)
        for block in sorted({row["block"] for row in base_rows}):
            keys = [row["key"] for row in base_rows if row["block"] == block]
            values = [shuffled[key] for key in keys]
            rng.shuffle(values)
            shuffled.update(zip(keys, values))
        permutations.append(shuffled)

    results = {}
    for variant, selected in variants.items():
        rows = [{**row, "features": {name: value for name, value in row["features"].items()
                                      if name in selected}} for row in base_rows]
        folds = _prepare_folds(rows)
        observed = _score(folds, labels)
        null = [_score(folds, shuffled)["accuracy"] for shuffled in permutations]
        observed["permutation_p_value"] = ((sum(value >= observed["accuracy"] for value in null) + 1)
                                             / (permutation_samples + 1))
        observed["feature_count"] = len(selected)
        observed["chance_accuracy"] = 0.25
        results[variant] = observed
    return {
        "format": "voxel-guidance.task-inference-ablation",
        "version": 1,
        "session_count": 12,
        "block_count": 3,
        "horizon_seconds": horizon_seconds,
        "classifier": "z-scored nearest task centroid",
        "validation": "leave-one-seed-block-out",
        "permutation_samples": permutation_samples,
        "selection_note": "120 seconds was selected after the exploratory prefix analysis as the earliest peak-accuracy horizon",
        "results": results,
    }
