from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from PIL import Image, ImageOps

from .ocr import OcrScan


PanelKind = Literal["inventory", "hero"]

PANEL_TITLES: dict[str, PanelKind] = {
    "inventory": "inventory",
    "hero": "hero",
}


class PanelOcrBackend(Protocol):
    def scan(self, image: Image.Image) -> OcrScan: ...


@dataclass(frozen=True)
class PanelObservation:
    format: str
    version: int
    panels: tuple[PanelKind, ...]
    status: Literal["recognized", "none", "uncertain"]
    confidence: float
    backend: str
    disclosure_policy: str


def recognize_panel_titles(
    scan: OcrScan, *, minimum_confidence: float = 0.80,
) -> PanelObservation:
    """Recognize only predeclared GW2 panel titles from a chat-masked frame."""
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum confidence must be between 0 and 1")
    if not scan.complete:
        return _result((), "uncertain", 0.0, scan.backend)
    recognized: dict[PanelKind, float] = {}
    ambiguous_title = False
    for token in scan.tokens:
        title = " ".join(token.text.casefold().split()).strip("[](){}:;,.!?")
        kind = PANEL_TITLES.get(title)
        if kind is None:
            continue
        if token.confidence < minimum_confidence:
            ambiguous_title = True
            continue
        recognized[kind] = max(recognized.get(kind, 0.0), token.confidence)
    if recognized:
        panels = tuple(sorted(recognized))
        return _result(panels, "recognized", min(recognized.values()), scan.backend)
    if ambiguous_title:
        return _result((), "uncertain", 0.0, scan.backend)
    return _result((), "none", 1.0, scan.backend)


def scan_panel_titles(image: Image.Image, ocr: PanelOcrBackend) -> PanelObservation:
    """Scan overlapping left and central areas after callers mask privacy zones."""
    if image.width < 640 or image.height < 480:
        raise ValueError("panel recognition requires at least a 640x480 frame")
    source = image.convert("RGB")
    areas = ((0.00, 0.04, 0.60, 0.78), (0.20, 0.08, 0.85, 0.78))
    tiles = tuple(source.crop((round(image.width * x1), round(image.height * y1),
                               round(image.width * x2), round(image.height * y2)))
                  for x1, y1, x2, y2 in areas)
    try:
        return scan_panel_tiles(tiles[0], tiles[1], ocr)
    finally:
        for tile in tiles:
            tile.close()


def scan_panel_tiles(left: Image.Image, center: Image.Image, ocr: PanelOcrBackend) -> PanelObservation:
    """Replay recognition from the two persisted, privacy-masked search tiles."""
    scans: list[OcrScan] = []
    for tile in (left, center):
        prepared = ImageOps.autocontrast(tile.convert("L")).resize(
            (tile.width * 2, tile.height * 2), Image.Resampling.LANCZOS,
        )
        scans.append(ocr.scan(prepared))
    combined = OcrScan(
        tokens=tuple(token for scan in scans for token in scan.tokens),
        backend="+".join(dict.fromkeys(scan.backend for scan in scans)),
        complete=all(scan.complete for scan in scans),
    )
    result = recognize_panel_titles(combined)
    anchored_hero = _anchored_hero_confidence(scans[0])
    if anchored_hero is None:
        return result
    panels = tuple(sorted(set(result.panels) | {"hero"}))
    confidence = min((result.confidence if result.panels else 1.0), anchored_hero)
    return _result(panels, "recognized", confidence, combined.backend)


def _anchored_hero_confidence(scan: OcrScan) -> float | None:
    """Recover stylized Small-UI Hero headers only inside the known left-tile anchor."""
    if not scan.complete:
        return None
    matches: list[float] = []
    for token in scan.tokens:
        title = " ".join(token.text.casefold().split()).strip("[](){}:;,.!?")
        box = token.box
        if (title == "hero" and token.confidence >= 0.45 and box is not None
                and ((0.35 <= box.x <= 0.47 and 0.05 <= box.y <= 0.15)
                     or (0.72 <= box.x <= 0.88 and 0.10 <= box.y <= 0.23))):
            matches.append(token.confidence)
    return max(matches, default=None)


def _result(
    panels: tuple[PanelKind, ...], status: Literal["recognized", "none", "uncertain"],
    confidence: float, backend: str,
) -> PanelObservation:
    return PanelObservation(
        format="zenith-vision.panel-observation", version=1, panels=panels,
        status=status, confidence=confidence, backend=backend,
        disclosure_policy="chat-masked-panel-title-allowlist-v1",
    )
