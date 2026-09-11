from __future__ import annotations

import math
from statistics import fmean, pstdev
from typing import Any

from .contract import ContractError, validate_event, validate_session
from .task_inference import TASKS, extract_prefix_features


def fit_guidance_model(sessions: Any, *, horizon_seconds: int = 120) -> dict[str, Any]:
    checked = [validate_session(events) for events in sessions]
    if len(checked) != 12 or len({e[0]["task_id"] for e in checked}) != 12:
        raise ContractError("guidance model requires the complete 12-session matrix")
    rows = [(events[0]["task_id"].rsplit("-", 1)[-1],
             extract_prefix_features(events, horizon_seconds)) for events in checked]
    names = sorted(rows[0][1])
    means = {name: fmean(row[name] for _, row in rows) for name in names}
    scales = {name: pstdev(row[name] for _, row in rows) or 1.0 for name in names}
    centroids = {}
    for task in TASKS:
        members = [[(row[name] - means[name]) / scales[name] for name in names]
                   for label, row in rows if label == task]
        centroids[task] = [fmean(values) for values in zip(*members)]
    return {"format": "voxel-guidance.guidance-model", "version": 1,
            "horizon_seconds": horizon_seconds, "features": names,
            "means": means, "scales": scales, "centroids": centroids,
            "training_sessions": 12,
            "claim_boundary": "four-task protocol classifier; not arbitrary intent inference"}


def predict_guidance(model: dict[str, Any], partial_events: Any) -> dict[str, Any]:
    if not isinstance(partial_events, list) or not partial_events:
        raise ContractError("live guidance requires observed events")
    checked = [validate_event(event) for event in partial_events]
    first = checked[0]
    if first["kind"] != "session_start":
        raise ContractError("live guidance requires a session start")
    for sequence, event in enumerate(checked):
        if event["sequence"] != sequence or event["session_id"] != first["session_id"]:
            raise ContractError("invalid partial session")
    if checked[-1]["kind"] == "session_end":
        complete = checked
    else:
        complete = checked + [{**checked[-1], "sequence": len(checked), "kind": "session_end",
                               "payload": {"reason": "explicit_stop"}}]
    features = extract_prefix_features(complete, int(model["horizon_seconds"]))
    names = model["features"]
    point = [(features[name] - model["means"][name]) / model["scales"][name] for name in names]
    distances = {task: fmean((value - center) ** 2 for value, center in zip(point, centroid))
                 for task, centroid in model["centroids"].items()}
    ranked = sorted(distances, key=lambda task: (distances[task], task))
    margin = distances[ranked[1]] - distances[ranked[0]]
    confidence_ratio = margin / max(distances[ranked[1]], 1e-12)
    return {"task": ranked[0], "margin": margin, "distances": distances,
            "confidence_ratio": confidence_ratio,
            "sufficient_evidence": confidence_ratio >= 0.15 and len(checked) >= 2}


def guidance_text(prediction: dict[str, Any]) -> str:
    if not prediction["sufficient_evidence"]:
        return (f"Low-confidence resemblance to {prediction['task']}; "
                "no guidance issued. Keep playing naturally.")
    return {
        "explore": "Exploration pattern detected. Keep a route you can reason back through.",
        "acquire": "Acquisition pattern detected. Keep the return path in mind as the kit grows.",
        "construct": "Construction pattern detected. Translate the plan into a minimal complete structure.",
        "recover": "Recovery pattern detected. Restore one viable state before expanding again.",
    }[prediction["task"]]
