from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class ReviewCandidateReceipt:
    format: str
    version: int
    created_at: str
    source_title: str
    source_instance: str
    source_class: str
    width: int
    height: int
    ocr_token_count: int
    mask_policy: str
    candidate_sha256: str
    dataset_admitted: bool = False


def save_review_candidate(
    image: Image.Image,
    directory: Path,
    *,
    source_title: str,
    source_instance: str,
    source_class: str,
    ocr_token_count: int,
    mask_policy: str,
    now: datetime | None = None,
) -> tuple[Path, Path, ReviewCandidateReceipt]:
    """Persist one private review candidate and a non-content receipt atomically."""
    if ocr_token_count < 0:
        raise ValueError("ocr_token_count cannot be negative")
    if not mask_policy.strip():
        raise ValueError("mask_policy is required")
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    current = now or datetime.now(timezone.utc)
    stamp = current.strftime("%Y%m%dT%H%M%S%fZ")
    candidate = directory / f"candidate-{stamp}.png"
    receipt_path = directory / f"candidate-{stamp}.json"
    candidate_temp = directory / f".{candidate.name}.tmp"
    receipt_temp = directory / f".{receipt_path.name}.tmp"
    try:
        image.convert("RGB").save(candidate_temp, format="PNG", optimize=True)
        os.chmod(candidate_temp, 0o600)
        digest = hashlib.sha256(candidate_temp.read_bytes()).hexdigest()
        receipt = ReviewCandidateReceipt(
            format="zenith-vision.review-candidate", version=2,
            created_at=current.isoformat(), source_title=source_title,
            source_instance=source_instance, source_class=source_class,
            width=image.width, height=image.height, ocr_token_count=ocr_token_count,
            mask_policy=mask_policy,
            candidate_sha256=digest,
        )
        receipt_temp.write_text(json.dumps(asdict(receipt), indent=2) + "\n", encoding="utf-8")
        os.chmod(receipt_temp, 0o600)
        os.replace(candidate_temp, candidate)
        os.replace(receipt_temp, receipt_path)
        return candidate, receipt_path, receipt
    finally:
        candidate_temp.unlink(missing_ok=True)
        receipt_temp.unlink(missing_ok=True)
