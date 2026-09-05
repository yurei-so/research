from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image

from .layout import UI_PROFILE_REGION_BOXES
from .models import VisionObservation, parse_timestamp
from .ocr import OcrFailure, OcrScan


class OcrBackend(Protocol):
    def scan(self, image: Image.Image) -> OcrScan: ...


@dataclass(frozen=True)
class ObjectiveTextObservation:
    format: str
    version: int
    captured_at: str
    text: str
    confidence: float
    token_count: int
    rejected_token_count: int
    retained_fraction: float
    complete: bool
    backend: str
    source_region: str
    source_crop_sha256: str
    disclosure_policy: str


def interpret_objectives_crop(
    image: Image.Image,
    ocr: OcrBackend,
    *,
    captured_at: str,
    source_crop_sha256: str,
    minimum_confidence: float = 0.70,
) -> ObjectiveTextObservation:
    """Recognize operator-approved objectives text or fail without partial output."""
    parse_timestamp(captured_at)
    if not re.fullmatch(r"[0-9a-f]{64}", source_crop_sha256):
        raise ValueError("source crop digest must be lowercase SHA-256")
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum confidence must be between 0 and 1")
    scan = ocr.scan(image)
    if not scan.complete:
        raise OcrFailure("objectives OCR was incomplete")
    if not scan.tokens:
        raise OcrFailure("objectives OCR returned no text")
    retained = tuple(token for token in scan.tokens if token.confidence >= minimum_confidence)
    rejected = len(scan.tokens) - len(retained)
    retained_fraction = len(retained) / len(scan.tokens)
    if len(retained) < 3 or retained_fraction < 0.50:
        raise OcrFailure("objectives OCR retained too little confident text")
    text = " ".join(" ".join(token.text.split()) for token in retained).strip()
    if not text or len(text) > 2048:
        raise OcrFailure("objectives OCR text length is invalid")
    if _looks_like_disallowed_identifier(text):
        raise OcrFailure("objectives OCR matched a disallowed identifier pattern")
    return ObjectiveTextObservation(
        format="zenith-vision.objective-text", version=1, captured_at=captured_at,
        text=text, confidence=min(token.confidence for token in retained),
        token_count=len(retained), rejected_token_count=rejected,
        retained_fraction=retained_fraction, complete=rejected == 0,
        backend=scan.backend, source_region="objectives",
        source_crop_sha256=source_crop_sha256,
        disclosure_policy="operator-approved-objectives-text-v1",
    )


def save_objective_observation(observation: ObjectiveTextObservation, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        temporary.write_text(json.dumps(asdict(observation), indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def objective_text_to_vision(observation: ObjectiveTextObservation) -> VisionObservation:
    """Adapt private objectives text into the provenance-carrying fusion contract."""
    return VisionObservation(
        kind="objective_text", label=observation.text, confidence=observation.confidence,
        captured_at=observation.captured_at,
        box=UI_PROFILE_REGION_BOXES["normal"]["objectives"],
        evidence={
            "source_region": observation.source_region,
            "source_crop_sha256": observation.source_crop_sha256,
            "ocr_backend": observation.backend,
            "disclosure_policy": observation.disclosure_policy,
            "complete": str(observation.complete).lower(),
            "retained_fraction": f"{observation.retained_fraction:.6f}",
        },
    )


def _looks_like_disallowed_identifier(text: str) -> bool:
    return bool(
        "@" in text
        or re.search(r"\bhttps?://|\bwww\.", text, flags=re.IGNORECASE)
        or re.search(r"\b[\w-]{2,32}\.\d{4}\b", text)
    )
