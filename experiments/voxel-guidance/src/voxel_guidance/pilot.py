from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from statistics import fmean
from typing import Any

from .contract import ContractError, validate_session_set
from .features import compile_session_features


COORDINATES = (
    "exploration_breadth", "route_closure", "plan_revision_rate",
    "resource_selectivity", "construction_allocation", "recovery_efficiency",
    "deliberation_latency",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def validate_protocol(protocol: Any, manifest: Any) -> dict[str, Any]:
    if not isinstance(protocol, dict) or protocol.get("format") != "voxel-guidance.protocol" or protocol.get("version") != 1:
        raise ContractError("unsupported pilot protocol")
    if protocol.get("status") != "frozen-before-pilot-collection":
        raise ContractError("pilot protocol is not frozen")
    if not isinstance(manifest, dict) or manifest.get("format") != "voxel-guidance.modpack-manifest" or manifest.get("version") != 1:
        raise ContractError("unsupported modpack manifest")
    blocks, tasks = protocol.get("blocks"), protocol.get("tasks")
    if not isinstance(blocks, list) or len(blocks) != protocol["design"]["block_count"]:
        raise ContractError("block count mismatch")
    if not isinstance(tasks, dict) or set(tasks) != {"explore", "acquire", "construct", "recover"}:
        raise ContractError("task definitions mismatch")
    if any(set(block.get("order", [])) != set(tasks) or len(block["order"]) != len(tasks) for block in blocks):
        raise ContractError("every block must schedule every task exactly once")
    if len({block.get("id") for block in blocks}) != len(blocks) or len({block.get("seed") for block in blocks}) != len(blocks):
        raise ContractError("block IDs and seeds must be unique")
    if protocol["design"]["session_count"] != len(blocks) * len(tasks):
        raise ContractError("session count mismatch")
    if tuple(protocol.get("fingerprint_coordinates", ())) != COORDINATES:
        raise ContractError("fingerprint coordinates changed")
    bridge = next((mod for mod in manifest.get("mods", []) if mod.get("file") == "voxel-guidance-bridge-0.1.0.jar"), None)
    if bridge is None or bridge.get("sha256") != protocol["apparatus"]["bridge_sha256"]:
        raise ContractError("bridge digest mismatch")
    if protocol["publication"].get("raw_events") or protocol["publication"].get("exact_routes"):
        raise ContractError("private raw data cannot enter the public projection")
    return {"protocol_digest": _digest(protocol), "manifest_digest": _digest(manifest)}


def _seconds(event: dict[str, Any], start: dict[str, Any]) -> float:
    from datetime import datetime
    parse = lambda value: datetime.fromisoformat(value[:-1] + "+00:00")
    return (parse(event["observed_at"]) - parse(start["observed_at"])).total_seconds()


def _recovery_efficiency(events: list[dict[str, Any]], duration: float) -> float | None:
    setback = next((event for event in events if event["kind"] == "marker" and event["payload"]["marker"] == "setback"), None)
    if setback is None:
        return None
    recovered = next((event for event in events if event["sequence"] > setback["sequence"]
                      and event["kind"] == "marker" and event["payload"]["marker"] == "recovered"), None)
    if recovered is None or duration <= 0:
        return 0.0
    return max(0.0, 1.0 - _seconds(recovered, setback) / duration)


def _plan_latency(events: list[dict[str, Any]], duration: float) -> float | None:
    marker = next((event for event in events if event["kind"] == "marker"
                   and event["payload"]["marker"] == "plan_started"), None)
    return _seconds(marker, events[0]) / duration if marker is not None and duration > 0 else None


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def compile_pilot(protocol: dict[str, Any], manifest: dict[str, Any], sessions: list[list[dict[str, Any]]]) -> dict[str, Any]:
    digests = validate_protocol(protocol, manifest)
    checked = validate_session_set(sessions)
    expected = {f"vg-{block['id']}-{task}": (block["id"], task)
                for block in protocol["blocks"] for task in block["order"]}
    observed: dict[str, list[dict[str, Any]]] = {}
    minimum = protocol["design"]["minimum_usable_duration_seconds"]
    maximum = protocol["design"]["maximum_usable_duration_seconds"]
    for events in checked:
        task_id = events[0]["task_id"]
        if task_id not in expected or task_id in observed:
            raise ContractError("unexpected or duplicate scheduled task")
        if events[0]["payload"]["protocol_id"] != "pilot-v1":
            raise ContractError("session is not bound to pilot-v1")
        if events[-1]["payload"]["reason"] != protocol["design"]["session_end_required"]:
            raise ContractError("pilot session requires explicit stop")
        duration = _seconds(events[-1], events[0])
        if not minimum <= duration <= maximum:
            raise ContractError("pilot session duration outside frozen bounds")
        task = expected[task_id][1]
        markers = [event["payload"]["marker"] for event in events if event["kind"] == "marker"]
        if any(markers.count(marker) != 1 for marker in protocol["tasks"][task]["required_markers"]):
            raise ContractError("required marker missing or duplicated")
        observed[task_id] = events
    if set(observed) != set(expected):
        raise ContractError("pilot session matrix is incomplete")

    blocks: dict[str, dict[str, float]] = {}
    quality = {"inventory_events_excluded_during_recovery": 0}
    for block in protocol["blocks"]:
        session_features = {}
        session_events = {}
        for task in block["order"]:
            task_id = f"vg-{block['id']}-{task}"
            session_events[task] = observed[task_id]
            session_features[task] = compile_session_features(observed[task_id])
            quality["inventory_events_excluded_during_recovery"] += session_features[task]["quality"]["inventory_events_excluded_during_recovery"]
        all_features = list(session_features.values())
        blocks[block["id"]] = {
            "exploration_breadth": session_features["explore"]["metrics"]["exploration_cells"]
                / (session_features["explore"]["duration_seconds"] / 60),
            "route_closure": 1.0 - session_features["acquire"]["metrics"]["route_directness"],
            "plan_revision_rate": fmean(item["metrics"]["plan_revision_rate"] for item in all_features),
            "resource_selectivity": session_features["acquire"]["metrics"]["resource_selectivity"],
            "construction_allocation": session_features["construct"]["metrics"]["construction_allocation"],
            "recovery_efficiency": _recovery_efficiency(session_events["recover"], session_features["recover"]["duration_seconds"]),
            "deliberation_latency": fmean(_plan_latency(session_events[task], session_features[task]["duration_seconds"])
                                          for task in block["order"]),
        }

    rng = random.Random(protocol["analysis"]["bootstrap_seed"])
    block_values = list(blocks.values())
    fingerprint = {}
    for coordinate in COORDINATES:
        values = [block[coordinate] for block in block_values]
        bootstrap = [fmean(rng.choice(values) for _ in values)
                     for _ in range(protocol["analysis"]["bootstrap_samples"])]
        leave_one_out = [fmean(value for j, value in enumerate(values) if j != index)
                         for index in range(len(values))]
        fingerprint[coordinate] = {
            "mean": fmean(values),
            "bootstrap_interval_95": [_quantile(bootstrap, 0.025), _quantile(bootstrap, 0.975)],
            "leave_one_block_out_range": [min(leave_one_out), max(leave_one_out)],
            "block_count": len(values),
        }
    return {
        "format": "voxel-guidance.fingerprint",
        "version": 1,
        "experiment_id": protocol["experiment_id"],
        **digests,
        "session_count": len(checked),
        "block_count": len(blocks),
        "coordinates": fingerprint,
        "quality": quality,
        "claim_boundary": "protocol-bound behavioral description; not identity or personality inference",
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain an object")
    return value
