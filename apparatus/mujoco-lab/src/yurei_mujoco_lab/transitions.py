from __future__ import annotations

from collections import Counter
from itertools import permutations

import numpy as np

from .simulate import POLICIES, simulate_sequence

FEATURE_NAMES = (
    "mean_speed", "speed_std", "max_speed", "path_distance", "displacement",
    "directness", "mean_turn", "control_energy", "control_change", "contact_rate",
)


def window_features(samples: list[dict]) -> np.ndarray:
    """Summarize motion without absolute position or fixture annotations."""
    if len(samples) < 3:
        raise ValueError("a feature window needs at least three samples")
    xy = np.array([(r["x"], r["y"]) for r in samples], dtype=float)
    velocity = np.array([(r["vx"], r["vy"]) for r in samples], dtype=float)
    controls = np.array([(r["control_x"], r["control_y"]) for r in samples], dtype=float)
    speed = np.linalg.norm(velocity, axis=1)
    steps = np.diff(xy, axis=0)
    distances = np.linalg.norm(steps, axis=1)
    path_distance = float(distances.sum())
    displacement = float(np.linalg.norm(xy[-1] - xy[0]))
    moving = velocity[speed > 0.08]
    mean_turn = 0.0
    if len(moving) > 2:
        headings = np.unwrap(np.arctan2(moving[:, 1], moving[:, 0]))
        mean_turn = float(np.mean(np.abs(np.diff(headings))))
    control_norm = np.linalg.norm(controls, axis=1)
    control_change = np.linalg.norm(np.diff(controls, axis=0), axis=1)
    return np.array([
        speed.mean(), speed.std(), speed.max(), path_distance, displacement,
        displacement / max(path_distance, 1e-9), mean_turn,
        np.mean(control_norm), np.mean(control_change),
        np.mean([r["contacts"] > 0 for r in samples]),
    ], dtype=float)


def causal_windows(replay: dict, *, window_seconds: float = 4.0,
                   stride_seconds: float = 1.0) -> list[dict]:
    if window_seconds <= 0 or stride_seconds <= 0:
        raise ValueError("window and stride must be positive")
    rows = replay["samples"]
    sample_hz = replay["sample_hz"]
    width = max(3, round(window_seconds * sample_hz))
    stride = max(1, round(stride_seconds * sample_hz))
    windows = []
    for end in range(width, len(rows) + 1, stride):
        chunk = rows[end - width:end]
        labels = Counter(row["phase"] for row in chunk)
        current = chunk[-1]["phase"]
        windows.append({
            "t": chunk[-1]["t"],
            "truth": current,
            "pure": labels[current] == len(chunk),
            "features": window_features(chunk),
        })
    return windows


def fit_prototypes(*, seconds: float = 24.0, sample_hz: int = 20,
                   window_seconds: float = 4.0, stride_seconds: float = 1.0) -> dict:
    labelled: list[tuple[str, np.ndarray]] = []
    # Train across varied predecessor states. A prototype learned only from a
    # fresh origin confuses strategy with where the agent happened to start.
    phase_seconds = seconds / 2
    for order in permutations(POLICIES):
        replay = simulate_sequence(list(order), seconds_per_phase=phase_seconds,
                                   sample_hz=sample_hz)
        labelled.extend((row["truth"], row["features"]) for row in causal_windows(
            replay, window_seconds=window_seconds, stride_seconds=stride_seconds)
            if row["pure"])
    matrix = np.stack([features for _, features in labelled])
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale < 1e-9] = 1.0
    prototypes = {
        name: np.stack([(features - mean) / scale for label, features in labelled if label == name]).mean(axis=0)
        for name in POLICIES
    }
    return {"mean": mean, "scale": scale, "prototypes": prototypes}


def classify(features: np.ndarray, model: dict) -> tuple[str, float, dict[str, float]]:
    normalized = (features - model["mean"]) / model["scale"]
    distances = {name: float(np.linalg.norm(normalized - centroid))
                 for name, centroid in model["prototypes"].items()}
    ordered = sorted(distances, key=distances.get)
    best, runner_up = ordered[:2]
    confidence = (distances[runner_up] - distances[best]) / max(distances[runner_up], 1e-9)
    return best, float(confidence), distances


def evaluate_threshold(threshold: float, *, phases: list[str] | None = None,
                       seconds_per_phase: float = 12.0, sample_hz: int = 20,
                       window_seconds: float = 4.0, stride_seconds: float = 1.0,
                       stable_windows: int = 2, cooldown_seconds: float = 5.0) -> dict:
    phases = phases or ["explore", "acquire", "construct", "recover"]
    replay = simulate_sequence(phases, seconds_per_phase=seconds_per_phase, sample_hz=sample_hz)
    model = fit_prototypes(sample_hz=sample_hz, window_seconds=window_seconds,
                           stride_seconds=stride_seconds)
    windows = causal_windows(replay, window_seconds=window_seconds, stride_seconds=stride_seconds)
    decisions = []
    run_label = None
    run_length = 0
    last_guidance = -float("inf")
    guidance = []
    current_guidance = None
    for row in windows:
        predicted, confidence, distances = classify(row["features"], model)
        accepted = predicted if confidence >= threshold else None
        if accepted == run_label and accepted is not None:
            run_length += 1
        else:
            run_label, run_length = accepted, 1 if accepted else 0
        stable = accepted if run_length >= stable_windows else None
        if stable and stable != current_guidance and row["t"] - last_guidance >= cooldown_seconds:
            guidance.append({"t": row["t"], "mode": stable, "truth": row["truth"]})
            current_guidance = stable
            last_guidance = row["t"]
        decisions.append({
            "t": row["t"], "truth": row["truth"], "pure": row["pure"],
            "prediction": predicted, "confidence": round(confidence, 6),
            "accepted": accepted, "stable": stable,
            "distances": {k: round(v, 6) for k, v in distances.items()},
        })
    pure = [r for r in decisions if r["pure"]]
    covered = [r for r in pure if r["accepted"]]
    transition_times = [(index * seconds_per_phase, phase) for index, phase in enumerate(phases[1:], 1)]
    latencies = []
    for time, phase in transition_times:
        phase_end = time + seconds_per_phase
        match = next((event for event in guidance
                      if time <= event["t"] < phase_end
                      and event["mode"] == phase and event["truth"] == phase), None)
        latencies.append({"phase": phase, "transition_t": time,
                          "detected_t": match["t"] if match else None,
                          "latency_seconds": round(match["t"] - time, 4) if match else None})
    true_changes = {(round(index * seconds_per_phase, 4), phase)
                    for index, phase in enumerate(phases)}
    return {
        "threshold": threshold,
        "window_count": len(decisions),
        "pure_window_count": len(pure),
        "coverage": round(len(covered) / max(len(pure), 1), 6),
        "accepted_accuracy": round(sum(r["accepted"] == r["truth"] for r in covered) / max(len(covered), 1), 6),
        "raw_accuracy": round(sum(r["prediction"] == r["truth"] for r in pure) / max(len(pure), 1), 6),
        "guidance_events": guidance,
        "guidance_per_minute": round(len(guidance) / (replay["seconds"] / 60), 4),
        "false_guidance_events": sum(event["mode"] != event["truth"] for event in guidance),
        "transition_latencies": latencies,
        "decisions": decisions,
    }


def calibration_report(*, thresholds: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3)) -> dict:
    phases = ["explore", "acquire", "construct", "recover"]
    sweep = [evaluate_threshold(value, phases=phases) for value in thresholds]
    safe = [row for row in sweep if row["false_guidance_events"] == 0]
    recommended = max(safe or sweep,
                      key=lambda row: (row["accepted_accuracy"], row["coverage"], -row["threshold"]))
    return {
        "format": "yurei-mujoco-lab.transition-calibration",
        "version": 1,
        "claim_boundary": "Synthetic apparatus calibration only; not Voxel Guidance evidence.",
        "feature_names": FEATURE_NAMES,
        "label_exclusions": ["phase", "phase_index", "phase_elapsed", "waypoint", "absolute_position"],
        "phases": phases,
        "selection_rule": "Among zero-false-guidance settings, maximize accepted accuracy, then coverage.",
        "recommended_threshold": recommended["threshold"],
        "threshold_sweep": sweep,
    }
