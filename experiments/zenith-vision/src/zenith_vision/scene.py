from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .fusion import fuse_observations
from .models import MumbleSnapshot, VisionObservation
from .panels import PanelObservation


@dataclass(frozen=True)
class SemanticSceneSnapshot:
    format: str
    version: int
    observed_at: str
    telemetry_status: str
    world: dict[str, Any] | None
    ui: dict[str, Any]
    provenance: dict[str, str]
    withheld: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_scene_snapshot(
    telemetry: MumbleSnapshot | None, panels: PanelObservation, *, observed_at: datetime | None = None,
) -> SemanticSceneSnapshot:
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    private_telemetry = replace(telemetry, character_name=None) if telemetry is not None else None
    label = "+".join(panels.panels) if panels.panels else "none"
    visual = VisionObservation(
        kind="ui_panels", label=label, confidence=panels.confidence,
        captured_at=now.isoformat(), evidence={
            "status": panels.status, "backend": panels.backend,
            "disclosure_policy": panels.disclosure_policy,
        },
    )
    fused = fuse_observations(private_telemetry, (visual,), now=now)
    return SemanticSceneSnapshot(
        format="zenith-vision.semantic-scene", version=1,
        observed_at=now.isoformat(), telemetry_status=fused.telemetry_status,
        world=fused.player,
        ui={"panel_status": panels.status, "panels": list(panels.panels),
            "confidence": panels.confidence},
        provenance={"world": fused.provenance.get("player", "unavailable"),
                    "ui": f"{panels.backend}:allowlist", "privacy": panels.disclosure_policy},
        withheld=("character_name", "raw_frame", "masked_frame", "raw_ocr_text"),
    )
