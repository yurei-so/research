from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


@dataclass(frozen=True)
class MumbleSnapshot:
    sequence: int
    connected: bool
    map_id: int | None
    position: tuple[float, float] | None
    heading: float | None
    character_name: str | None
    timestamp: str
    source: Literal["mumblelink", "mock"] = "mumblelink"
    game_build: int | None = None
    in_combat: bool | None = None
    camera_position: tuple[float, float, float] | None = None
    camera_front: tuple[float, float, float] | None = None

    @classmethod
    def from_relay(cls, payload: dict[str, Any]) -> "MumbleSnapshot":
        if payload.get("type") != "player":
            raise ValueError("telemetry payload type must be 'player'")
        parse_timestamp(str(payload["timestamp"]))
        source = payload.get("source", "mumblelink")
        if source not in {"mumblelink", "mock"}:
            raise ValueError("unsupported telemetry source")
        return cls(
            sequence=int(payload["sequence"]), connected=bool(payload["connected"]),
            map_id=_optional_int(payload.get("mapId")), position=_tuple(payload.get("position"), 2),
            heading=_optional_float(payload.get("heading")), character_name=_optional_str(payload.get("characterName")),
            timestamp=str(payload["timestamp"]), source=source,
            game_build=_optional_int(payload.get("gameBuild")),
            in_combat=payload.get("inCombat") if isinstance(payload.get("inCombat"), bool) else None,
            camera_position=_tuple(payload.get("cameraPosition"), 3), camera_front=_tuple(payload.get("cameraFront"), 3),
        )


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(0.0 <= value <= 1.0 for value in values):
            raise ValueError("bounding box coordinates must be normalized to 0..1")
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("bounding box extends beyond the frame")


@dataclass(frozen=True)
class VisionObservation:
    kind: str
    label: str
    confidence: float
    captured_at: str
    box: BoundingBox | None = None
    evidence: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.kind or not self.label:
            raise ValueError("vision observation kind and label are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        parse_timestamp(self.captured_at)
        if self.evidence is not None and any(
            not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip()
            for key, value in self.evidence.items()
        ):
            raise ValueError("vision evidence keys and values must be non-empty strings")


@dataclass(frozen=True)
class FusedObservation:
    observed_at: str
    telemetry_status: Literal["current", "stale", "disconnected", "missing"]
    player: dict[str, Any] | None
    visual: tuple[VisionObservation, ...]
    rejected_visual: tuple[dict[str, str], ...]
    provenance: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _tuple(value: Any, length: int) -> tuple[float, ...] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"expected a {length}-element vector")
    return tuple(float(item) for item in value)
