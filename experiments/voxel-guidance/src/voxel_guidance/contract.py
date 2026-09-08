from __future__ import annotations

import math
from datetime import datetime
from typing import Any


class ContractError(ValueError):
    pass


INSTANCE_ID = "Voxel Guidance Lab"
EVENT_FORMAT = "voxel-guidance.event"
KINDS = {
    "session_start", "position_sample", "inventory_delta", "block_action",
    "damage", "death", "respawn", "marker", "session_end",
}
PAYLOAD_KEYS = {
    "session_start": {"protocol_id"},
    "position_sample": {"x", "y", "z", "dimension"},
    "inventory_delta": {"category", "delta"},
    "block_action": {"action", "category", "count"},
    "damage": {"amount", "source_category"},
    "death": set(),
    "respawn": set(),
    "marker": {"marker"},
    "session_end": {"reason"},
}
ALLOWED = {
    "dimension": {"overworld", "nether", "end"},
    "inventory_category": {"building", "resource", "tool", "food", "other"},
    "block_action": {"placed", "broken"},
    "block_category": {"building", "resource", "functional", "other"},
    "damage_source": {"environment", "mob", "player", "other"},
    "marker": {"plan_started", "plan_revised", "setback", "recovered", "task_complete"},
    "end_reason": {"completed", "stopped", "explicit_stop", "disconnected", "crash_recovered"},
}


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError("observed_at must be an RFC3339 UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ContractError("invalid observed_at") from error


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ContractError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise ContractError(f"{name} must be at least {minimum}")
    return result


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ContractError("event must be an object")
    required = {"format", "version", "session_id", "sequence", "observed_at", "instance_id", "task_id", "kind", "payload"}
    if set(event) != required:
        raise ContractError("event envelope has missing or unknown fields")
    if event["format"] != EVENT_FORMAT or event["version"] != 1:
        raise ContractError("unsupported event contract")
    if event["instance_id"] != INSTANCE_ID:
        raise ContractError("event is not from the toolkit-owned lab instance")
    if not isinstance(event["session_id"], str) or not event["session_id"]:
        raise ContractError("invalid session_id")
    if not isinstance(event["task_id"], str) or not event["task_id"]:
        raise ContractError("invalid task_id")
    if isinstance(event["sequence"], bool) or not isinstance(event["sequence"], int) or event["sequence"] < 0:
        raise ContractError("invalid sequence")
    _timestamp(event["observed_at"])
    kind, payload = event["kind"], event["payload"]
    if kind not in KINDS or not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS[kind]:
        raise ContractError("invalid event kind or payload shape")
    if kind == "position_sample":
        for axis in ("x", "y", "z"):
            _number(payload[axis], axis)
        if payload["dimension"] not in ALLOWED["dimension"]:
            raise ContractError("invalid dimension")
    elif kind == "inventory_delta":
        if payload["category"] not in ALLOWED["inventory_category"] or isinstance(payload["delta"], bool) or not isinstance(payload["delta"], int) or payload["delta"] == 0:
            raise ContractError("invalid inventory delta")
    elif kind == "block_action":
        if payload["action"] not in ALLOWED["block_action"] or payload["category"] not in ALLOWED["block_category"]:
            raise ContractError("invalid block action")
        if isinstance(payload["count"], bool) or not isinstance(payload["count"], int) or payload["count"] < 1:
            raise ContractError("invalid block count")
    elif kind == "damage":
        _number(payload["amount"], "damage amount", minimum=0)
        if payload["source_category"] not in ALLOWED["damage_source"]:
            raise ContractError("invalid damage source")
    elif kind == "marker" and payload["marker"] not in ALLOWED["marker"]:
        raise ContractError("invalid marker")
    elif kind == "session_end" and payload["reason"] not in ALLOWED["end_reason"]:
        raise ContractError("invalid end reason")
    elif kind == "session_start" and (not isinstance(payload["protocol_id"], str) or not payload["protocol_id"]):
        raise ContractError("invalid protocol_id")
    return event


def validate_session(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list) or len(events) < 2:
        raise ContractError("session must contain at least start and end events")
    checked = [validate_event(event) for event in events]
    first = checked[0]
    if first["kind"] != "session_start" or checked[-1]["kind"] != "session_end":
        raise ContractError("session boundaries are missing or misplaced")
    identity = (first["session_id"], first["task_id"], first["instance_id"])
    prior = None
    for sequence, event in enumerate(checked):
        if event["sequence"] != sequence:
            raise ContractError("event sequence must be contiguous and zero-based")
        if (event["session_id"], event["task_id"], event["instance_id"]) != identity:
            raise ContractError("cross-session or cross-task event detected")
        observed = _timestamp(event["observed_at"])
        if prior is not None and observed < prior:
            raise ContractError("event timestamps moved backwards")
        prior = observed
        if sequence and sequence < len(checked) - 1 and event["kind"] in {"session_start", "session_end"}:
            raise ContractError("duplicate session boundary")
    return checked


def validate_session_set(sessions: Any) -> list[list[dict[str, Any]]]:
    if not isinstance(sessions, list) or not sessions:
        raise ContractError("session set must be a nonempty array")
    checked = [validate_session(events) for events in sessions]
    identities = [events[0]["session_id"] for events in checked]
    if len(set(identities)) != len(identities):
        raise ContractError("duplicate session_id in session set")
    return checked
