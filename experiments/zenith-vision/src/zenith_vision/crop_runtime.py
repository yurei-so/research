from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .layout import propose_profile_regions


PROMOTED_UI_PROFILES = ("normal",)


@dataclass(frozen=True)
class CropArtifact:
    kind: str
    file: str
    sha256: str
    width: int
    height: int
    box: tuple[float, float, float, float]


@dataclass(frozen=True)
class CropReceipt:
    format: str
    version: int
    created_at: str
    ui_scale: str
    profile_source: str
    source_width: int
    source_height: int
    source_artifact_written: bool
    artifacts: tuple[CropArtifact, ...]


def persist_profile_crops(
    frame: Image.Image,
    destination: Path,
    *,
    ui_scale: str,
    now: datetime | None = None,
) -> tuple[Path, CropReceipt]:
    """Persist only promoted HUD crops and a content-free receipt."""
    if ui_scale not in PROMOTED_UI_PROFILES:
        raise ValueError("UI profile is not promoted for runtime cropping")
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("crop runtime destination must be empty")
    destination.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(destination, 0o700)
    source = frame.convert("RGB")
    proposals = propose_profile_regions(source.width, source.height, ui_scale=ui_scale)
    artifacts: list[CropArtifact] = []
    for proposal in proposals:
        box = proposal.box
        pixels = (
            round(box.x * source.width), round(box.y * source.height),
            round((box.x + box.width) * source.width),
            round((box.y + box.height) * source.height),
        )
        path = destination / f"{proposal.kind}.png"
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            crop = source.crop(pixels)
            crop.save(temporary, format="PNG", optimize=True)
            os.chmod(temporary, 0o600)
            digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        artifacts.append(CropArtifact(
            kind=proposal.kind, file=path.name, sha256=digest,
            width=pixels[2] - pixels[0], height=pixels[3] - pixels[1],
            box=(box.x, box.y, box.width, box.height),
        ))
    current = now or datetime.now(timezone.utc)
    receipt = CropReceipt(
        format="zenith-vision.crop-receipt", version=1, created_at=current.isoformat(),
        ui_scale=ui_scale, profile_source=proposals[0].source,
        source_width=source.width, source_height=source.height,
        source_artifact_written=False, artifacts=tuple(artifacts),
    )
    receipt_path = destination / "receipt.json"
    temporary = receipt_path.with_name(".receipt.json.tmp")
    try:
        temporary.write_text(json.dumps(asdict(receipt), indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, receipt_path)
    finally:
        temporary.unlink(missing_ok=True)
    return receipt_path, receipt
