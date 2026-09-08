from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any

from .experiment import ContractError


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ContractError(f"{path}: expected object")
    return value


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position); upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def compile_fingerprints(protocol_path: Path, reveal_path: Path, judgments_path: Path,
                         *, bootstrap_samples: int = 10_000, seed: int = 20260905) -> dict[str, Any]:
    protocol, reveal, judgments = map(_load, (protocol_path, reveal_path, judgments_path))
    if reveal.get("bundle_digest") != judgments.get("bundle_digest"):
        raise ContractError("reveal and judgments do not match")
    reveal_by_id = {item["item_id"]: item for item in reveal["items"]}
    rows = [{**reveal_by_id[item["item_id"]], **item} for item in judgments["judgments"]]
    models = sorted({row["model_id"] for row in rows})
    cases = sorted({row["case_id"] for row in rows})
    dimensions = protocol["dimensions"]
    neutral = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    guarded = defaultdict(lambda: defaultdict(list))
    for row in rows:
        for dimension in dimensions:
            if row["variant_id"] == "neutral":
                neutral[row["model_id"]][row["case_id"]][dimension].append(row["scores"][dimension])
            else:
                guarded[row["model_id"]][dimension].append(row["scores"][dimension])
    rng = random.Random(seed)
    output = {"format": "narrative-steering.fingerprints", "version": 1,
        "experiment_id": protocol["experiment_id"], "bundle_digest": judgments["bundle_digest"],
        "bootstrap": {"unit": "story_state", "samples": bootstrap_samples, "seed": seed}, "models": {}}
    for model in models:
        coordinates = {}
        for dimension in dimensions:
            raw_by_case = {case: fmean(neutral[model][case][dimension]) for case in cases}
            relative_by_case = {}
            for case in cases:
                center = fmean(fmean(neutral[other][case][dimension]) for other in models)
                relative_by_case[case] = raw_by_case[case] - center
            bootstrap = [fmean(relative_by_case[rng.choice(cases)] for _ in cases)
                         for _ in range(bootstrap_samples)]
            leave_one_out = [fmean(relative_by_case[case] for case in cases if case != omitted)
                             for omitted in cases]
            relative_mean = fmean(relative_by_case.values())
            stable_direction = sum((value > 0) == (relative_mean > 0) for value in relative_by_case.values())
            coordinates[dimension] = {
                "neutral_raw_mean": fmean(raw_by_case.values()),
                "neutral_relative_mean": relative_mean,
                "relative_95_interval": [_percentile(bootstrap, .025), _percentile(bootstrap, .975)],
                "relative_by_state": relative_by_case,
                "leave_one_state_out_range": [min(leave_one_out), max(leave_one_out)],
                "same_direction_states": stable_direction,
                "agency_guard_shift": fmean(guarded[model][dimension]) -
                    fmean(value for case in cases for value in neutral[model][case][dimension]),
            }
        output["models"][model] = {"coordinates": coordinates,
            "mean_human_confidence": fmean(row["confidence"] for row in rows if row["model_id"] == model)}
    return output


def calibrate_scorer(protocol_path: Path, reveal_path: Path, human_path: Path,
                     automated_path: Path) -> dict[str, Any]:
    protocol, reveal, human, automated = map(_load, (protocol_path, reveal_path, human_path, automated_path))
    if len({reveal.get("bundle_digest"), human.get("bundle_digest"), automated.get("bundle_digest")}) != 1:
        raise ContractError("calibration inputs do not share a bundle")
    reveal_by_id = {item["item_id"]: item for item in reveal["items"]}
    human_by_id = {item["item_id"]: item for item in human["judgments"]}
    auto_by_id = {item["item_id"]: item for item in automated["judgments"]}
    if set(reveal_by_id) != set(human_by_id) or set(reveal_by_id) != set(auto_by_id):
        raise ContractError("calibration requires identical complete item sets")
    result = {"format": "narrative-steering.scorer-calibration", "version": 1,
        "bundle_digest": human["bundle_digest"], "scorer": automated.get("scorer"), "dimensions": {}}
    for dimension in protocol["dimensions"]:
        raw_errors = []; corrected_errors = []; within_one = []; sign_matches = []
        for item_id, reveal_item in reveal_by_id.items():
            human_score = human_by_id[item_id]["scores"][dimension]
            auto_score = auto_by_id[item_id]["scores"][dimension]
            raw_errors.append(abs(auto_score - human_score))
            training_ids = [other_id for other_id, other in reveal_by_id.items()
                            if other["case_id"] != reveal_item["case_id"]]
            bias = fmean(auto_by_id[x]["scores"][dimension] - human_by_id[x]["scores"][dimension]
                         for x in training_ids)
            corrected = max(protocol["score_min"], min(protocol["score_max"], auto_score - bias))
            corrected_errors.append(abs(corrected - human_score))
            within_one.append(abs(corrected - human_score) <= 1)
            if human_score != 0:
                sign_matches.append((corrected > 0) == (human_score > 0))
        metrics = {"raw_mae": fmean(raw_errors), "leave_one_state_out_bias_corrected_mae": fmean(corrected_errors),
            "within_one_rate": fmean(within_one), "nonzero_sign_agreement": fmean(sign_matches) if sign_matches else None}
        metrics["eligible_for_expansion"] = (metrics["leave_one_state_out_bias_corrected_mae"] <= .75
            and metrics["within_one_rate"] >= .8 and (metrics["nonzero_sign_agreement"] or 0) >= .7)
        result["dimensions"][dimension] = metrics
    return result
