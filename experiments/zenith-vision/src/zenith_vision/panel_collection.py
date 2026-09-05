from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class PanelTileArtifact:
    kind: str
    file: str
    sha256: str
    width: int
    height: int


def extract_panel_search_tiles(masked_frame: Image.Image) -> dict[str, Image.Image]:
    """Extract overlapping panel-search tiles from an already privacy-masked frame."""
    if masked_frame.width < 640 or masked_frame.height < 480:
        raise ValueError("panel collection requires at least a 640x480 frame")
    areas = {
        "left": (0.00, 0.04, 0.60, 0.78),
        "center": (0.20, 0.08, 0.85, 0.78),
    }
    return {
        kind: masked_frame.crop((round(masked_frame.width * x1), round(masked_frame.height * y1),
                                 round(masked_frame.width * x2), round(masked_frame.height * y2)))
        for kind, (x1, y1, x2, y2) in areas.items()
    }


def persist_panel_sample(
    masked_frame: Image.Image, destination: Path, *, sample_id: str,
) -> tuple[PanelTileArtifact, ...]:
    """Persist only masked search tiles; never persist the source frame."""
    if not sample_id or not sample_id.replace("-", "").isalnum():
        raise ValueError("sample id must contain only letters, numbers, and hyphens")
    destination.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(destination, 0o700)
    artifacts: list[PanelTileArtifact] = []
    for kind, tile in extract_panel_search_tiles(masked_frame).items():
        path = destination / f"{sample_id}-{kind}.png"
        if path.exists():
            raise FileExistsError("panel sample already exists")
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            tile.save(temporary, format="PNG", optimize=True)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
            tile.close()
        artifacts.append(PanelTileArtifact(
            kind=kind, file=path.name, sha256=_sha256(path), width=path_image_width(path),
            height=path_image_height(path),
        ))
    return tuple(artifacts)


def write_panel_batch_manifest(destination: Path, payload: dict[str, object]) -> Path:
    path = destination / "manifest.json"
    temporary = path.with_name(".manifest.json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return path


def artifacts_to_dict(artifacts: tuple[PanelTileArtifact, ...]) -> list[dict[str, object]]:
    return [asdict(artifact) for artifact in artifacts]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_image_width(path: Path) -> int:
    with Image.open(path) as image:
        return image.width


def path_image_height(path: Path) -> int:
    with Image.open(path) as image:
        return image.height
