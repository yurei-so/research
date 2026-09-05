from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal

from .models import FusedObservation, MumbleSnapshot, VisionObservation, parse_timestamp


AUTHORITATIVE_VISION_KINDS = frozenset({"map", "location", "position", "heading", "character", "combat", "camera"})


def fuse_observations(
    telemetry: MumbleSnapshot | None,
    visual: Iterable[VisionObservation],
    *,
    now: datetime | None = None,
    max_telemetry_age: timedelta = timedelta(seconds=2),
) -> FusedObservation:
    """Fuse observations while refusing visual substitutes for MumbleLink state."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("now must include a timezone")
    status = _telemetry_status(telemetry, current_time, max_telemetry_age)
    accepted: list[VisionObservation] = []
    rejected: list[dict[str, str]] = []
    for observation in visual:
        if observation.kind.casefold() in AUTHORITATIVE_VISION_KINDS:
            rejected.append({"kind": observation.kind, "reason": "reserved_for_telemetry"})
        else:
            accepted.append(observation)
    player = None
    provenance: dict[str, str] = {"visual": "vision"}
    if status == "current" and telemetry is not None:
        player = {
            "map_id": telemetry.map_id, "position": telemetry.position, "heading": telemetry.heading,
            "character_name": telemetry.character_name, "game_build": telemetry.game_build,
            "in_combat": telemetry.in_combat, "camera_position": telemetry.camera_position,
            "camera_front": telemetry.camera_front,
        }
        provenance["player"] = telemetry.source
    return FusedObservation(current_time.isoformat(), status, player, tuple(accepted), tuple(rejected), provenance)


def _telemetry_status(
    telemetry: MumbleSnapshot | None, now: datetime, max_age: timedelta
) -> Literal["current", "stale", "disconnected", "missing"]:
    if telemetry is None:
        return "missing"
    if not telemetry.connected:
        return "disconnected"
    age = now - parse_timestamp(telemetry.timestamp)
    if age < timedelta(0) or age > max_age:
        return "stale"
    return "current"
