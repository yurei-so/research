from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from .contract import validate_session


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compile_session_features(events: Any, *, cell_size: int = 16) -> dict[str, Any]:
    """Compile transparent session metrics; this does not create a fingerprint."""
    checked = validate_session(events)
    positions = [event for event in checked if event["kind"] == "position_sample"]
    path_distance = 0.0
    for previous, current in zip(positions, positions[1:]):
        if previous["payload"]["dimension"] == current["payload"]["dimension"]:
            path_distance += math.dist(
                (previous["payload"]["x"], previous["payload"]["z"]),
                (current["payload"]["x"], current["payload"]["z"]),
            )
    visited = {
        (event["payload"]["dimension"], math.floor(event["payload"]["x"] / cell_size),
         math.floor(event["payload"]["z"] / cell_size))
        for event in positions
    }
    direct_distance = 0.0
    if len(positions) > 1 and positions[0]["payload"]["dimension"] == positions[-1]["payload"]["dimension"]:
        direct_distance = math.dist(
            (positions[0]["payload"]["x"], positions[0]["payload"]["z"]),
            (positions[-1]["payload"]["x"], positions[-1]["payload"]["z"]),
        )
    markers = [event for event in checked if event["kind"] == "marker"]
    marker_counts = {name: sum(event["payload"]["marker"] == name for event in markers)
                     for name in ("plan_started", "plan_revised", "setback", "recovered", "task_complete")}
    acquired = [event for event in checked if event["kind"] == "inventory_delta" and event["payload"]["delta"] > 0]
    acquired_total = sum(event["payload"]["delta"] for event in acquired)
    selected_resources = sum(event["payload"]["delta"] for event in acquired
                             if event["payload"]["category"] == "resource")
    block_events = [event for event in checked if event["kind"] == "block_action"]
    placed = sum(event["payload"]["count"] for event in block_events if event["payload"]["action"] == "placed")
    broken = sum(event["payload"]["count"] for event in block_events if event["payload"]["action"] == "broken")
    duration = (_time(checked[-1]["observed_at"]) - _time(checked[0]["observed_at"])).total_seconds()
    marker_latency = ((_time(markers[0]["observed_at"]) - _time(checked[0]["observed_at"])).total_seconds()
                      if markers else None)
    return {
        "format": "voxel-guidance.session-features",
        "version": 1,
        "session_id": checked[0]["session_id"],
        "task_id": checked[0]["task_id"],
        "event_count": len(checked),
        "duration_seconds": duration,
        "metrics": {
            "exploration_cells": len(visited),
            "path_distance": path_distance,
            "route_directness": _ratio(direct_distance, path_distance),
            "plan_revision_rate": _ratio(marker_counts["plan_revised"], marker_counts["plan_started"]),
            "resource_selectivity": _ratio(selected_resources, acquired_total),
            "setback_recovery_rate": _ratio(marker_counts["recovered"], marker_counts["setback"]),
            "construction_allocation": _ratio(placed, placed + broken + acquired_total),
            "first_marker_latency_fraction": _ratio(marker_latency, duration) if marker_latency is not None else None,
        },
    }
