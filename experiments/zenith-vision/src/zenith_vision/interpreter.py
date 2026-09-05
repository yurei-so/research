from __future__ import annotations

from dataclasses import asdict, dataclass
from math import hypot
from typing import Any, Mapping, Sequence

from .scene import SemanticSceneSnapshot


@dataclass(frozen=True)
class InterpretedScene:
    format: str
    version: int
    observed_at: str
    situation: dict[str, Any]
    map_context: dict[str, Any]
    nearby: tuple[dict[str, Any], ...]
    guidance: tuple[dict[str, str], ...]
    unknowns: tuple[str, ...]
    provenance: dict[str, str]
    withheld: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interpret_scene(
    scene: SemanticSceneSnapshot,
    map_data: Mapping[str, Any] | None,
    *, map_error: str | None = None, nearby_limit: int = 3,
) -> InterpretedScene:
    """Summarize one privacy-bounded scene without guessing hidden state."""
    if nearby_limit < 0:
        raise ValueError("nearby_limit must not be negative")

    world = scene.world or {}
    map_id = world.get("map_id")
    position = _point(world.get("position"))
    panels = tuple(str(item) for item in scene.ui.get("panels", ()))
    in_combat = world.get("in_combat")
    unknowns: list[str] = []

    if scene.telemetry_status != "current":
        mode = "world_state_unavailable"
        unknowns.extend(("map_context", "position", "combat_state"))
    elif in_combat is True:
        mode = "combat"
    elif in_combat is False:
        mode = "exploration"
    else:
        mode = "world"
        unknowns.append("combat_state")

    ui_focus = "+".join(panels) if panels else "world"
    situation = {"mode": mode, "ui_focus": ui_focus, "telemetry_status": scene.telemetry_status}
    valid_map = (
        map_data is not None and isinstance(map_id, int)
        and map_data.get("id") == map_id and isinstance(map_data.get("name"), str)
    )
    if valid_map:
        map_context = {
            "status": "resolved", "id": map_id, "name": map_data["name"],
            "region": map_data.get("regionName"), "continent": map_data.get("continentName"),
            "level_range": [map_data.get("minLevel"), map_data.get("maxLevel")],
        }
    else:
        map_context = {
            "status": "unavailable", "id": map_id if isinstance(map_id, int) else None,
            "reason": map_error or ("no_current_map" if map_id is None else "map_not_resolved"),
        }
        if "map_context" not in unknowns:
            unknowns.append("map_context")

    nearby = _nearby(map_data, position, nearby_limit) if valid_map and position else ()
    if scene.telemetry_status == "current" and position is None:
        unknowns.append("position")
    if valid_map and position is not None and not nearby:
        unknowns.append("nearby_landmarks")

    guidance: list[dict[str, str]] = []
    if mode == "world_state_unavailable":
        guidance.append({"kind": "wait_for_telemetry", "message":
            "World guidance is withheld until current MumbleLink telemetry is available.",
            "basis": "telemetry_status"})
    elif in_combat is True:
        guidance.append({"kind": "combat_safe", "message":
            "Keep guidance brief and avoid management actions while combat is active.",
            "basis": "mumblelink.in_combat"})
    elif panels:
        guidance.append({"kind": "panel_context", "message":
            f"The current task context is the allowlisted {ui_focus} panel.",
            "basis": "window_ocr.panel_allowlist"})
    else:
        guidance.append({"kind": "world_context", "message":
            "No allowlisted management panel is open; treat this as world navigation context.",
            "basis": "window_ocr.panel_allowlist"})
    if nearby:
        guidance.append({"kind": "nearby_reference", "message":
            f"Nearest public map reference: {nearby[0]['name']} ({nearby[0]['kind']}).",
            "basis": "zenith.map_metadata+mumblelink.position"})

    return InterpretedScene(
        format="zenith-vision.interpreted-scene", version=1, observed_at=scene.observed_at,
        situation=situation, map_context=map_context, nearby=nearby, guidance=tuple(guidance),
        unknowns=tuple(dict.fromkeys(unknowns)),
        provenance={"world": scene.provenance.get("world", "unavailable"),
                    "ui": scene.provenance.get("ui", "unavailable"),
                    "map": "zenith-loopback:gw2-public-api" if valid_map else "unavailable",
                    "composition": "deterministic-rules-v1"},
        withheld=tuple(dict.fromkeys((*scene.withheld, "raw_prompt", "model_completion"))),
    )


def _nearby(map_data: Mapping[str, Any] | None, position: tuple[float, float] | None,
            limit: int) -> tuple[dict[str, Any], ...]:
    if map_data is None or position is None or limit == 0:
        return ()
    candidates: list[dict[str, Any]] = []
    for collection, fallback_kind in (("pointsOfInterest", "point_of_interest"), ("hearts", "heart")):
        values = map_data.get(collection, ())
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            continue
        for value in values:
            if not isinstance(value, Mapping) or not isinstance(value.get("name"), str):
                continue
            coordinate = _point(value.get("coordinate"))
            if coordinate is None:
                continue
            candidates.append({"kind": str(value.get("kind") or fallback_kind),
                "name": value["name"], "distance_game_units": round(
                    hypot(coordinate[0] - position[0], coordinate[1] - position[1]), 1)})
    candidates.sort(key=lambda value: (value["distance_game_units"], value["kind"], value["name"]))
    return tuple(candidates[:limit])


def _point(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
