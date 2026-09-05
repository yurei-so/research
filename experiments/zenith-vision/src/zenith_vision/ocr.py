from __future__ import annotations

import csv
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

from .models import BoundingBox


class OcrUnavailable(RuntimeError):
    pass


class OcrFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class OcrToken:
    text: str
    confidence: float
    box: BoundingBox | None = None


@dataclass(frozen=True)
class OcrScan:
    tokens: tuple[OcrToken, ...]
    backend: str
    complete: bool


@dataclass(frozen=True)
class TextSafetyDecision:
    safe_to_reveal: bool
    reason: str
    token_count: int


class TesseractOcr:
    """Bounded local OCR. Source pixels are written only to an owner-only temp file."""

    def __init__(
        self, executable: str = "tesseract", timeout_seconds: float = 10.0,
        page_segmentation_mode: int = 6,
    ) -> None:
        resolved = shutil.which(executable)
        if resolved is None:
            raise OcrUnavailable("tesseract executable is not installed")
        self.executable = resolved
        self.timeout_seconds = timeout_seconds
        if page_segmentation_mode not in {6, 11}:
            raise ValueError("page segmentation mode must be 6 or 11")
        self.page_segmentation_mode = page_segmentation_mode

    def scan(self, image: Image.Image) -> OcrScan:
        with tempfile.TemporaryDirectory(prefix="zenith-vision-ocr-") as directory:
            path = Path(directory) / "region.png"
            image.convert("RGB").save(path, format="PNG")
            try:
                result = subprocess.run(
                    [self.executable, str(path), "stdout", "--psm", str(self.page_segmentation_mode), "tsv"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=self.timeout_seconds, text=True,
                )
            except subprocess.TimeoutExpired as error:
                raise OcrFailure("tesseract timed out") from error
            if result.returncode != 0:
                raise OcrFailure(f"tesseract exited with status {result.returncode}")
            return parse_tesseract_tsv(result.stdout, image_size=image.size)


def parse_tesseract_tsv(value: str, *, image_size: tuple[int, int] | None = None) -> OcrScan:
    try:
        rows = csv.DictReader(io.StringIO(value), delimiter="\t")
        if rows.fieldnames is None or not {"text", "conf"}.issubset(rows.fieldnames):
            raise ValueError("missing TSV columns")
        tokens: list[OcrToken] = []
        for row in rows:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            confidence = float(row.get("conf") or "-1") / 100.0
            box = _parse_box(row, image_size) if image_size is not None else None
            tokens.append(OcrToken(text=text, confidence=max(0.0, min(1.0, confidence)), box=box))
        return OcrScan(tokens=tuple(tokens), backend="tesseract", complete=True)
    except (csv.Error, TypeError, ValueError) as error:
        raise OcrFailure("invalid tesseract TSV output") from error


def assess_text_safety(
    scan: OcrScan,
    *,
    allowed_text: Iterable[str] = (),
    minimum_confidence: float = 0.85,
) -> TextSafetyDecision:
    """Fail closed unless OCR completed and every token is confidently allowlisted."""
    if not scan.complete:
        return TextSafetyDecision(False, "ocr_incomplete", len(scan.tokens))
    allowed = {_normalize(item) for item in allowed_text if _normalize(item)}
    for token in scan.tokens:
        if token.confidence < minimum_confidence:
            return TextSafetyDecision(False, "ambiguous_text", len(scan.tokens))
        if _normalize(token.text) not in allowed:
            return TextSafetyDecision(False, "unapproved_text", len(scan.tokens))
    return TextSafetyDecision(True, "ocr_clean", len(scan.tokens))


def mask_ocr_tokens(
    image: Image.Image, scan: OcrScan, *, padding_pixels: int = 4,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """Mask every recognized token; fail closed when OCR geometry is incomplete."""
    if not scan.complete:
        raise OcrFailure("cannot mask an incomplete OCR scan")
    if padding_pixels < 0 or padding_pixels > 100:
        raise ValueError("padding_pixels must be between 0 and 100")
    result = image.convert("RGB").copy()
    from PIL import ImageDraw
    draw = ImageDraw.Draw(result)
    for token in scan.tokens:
        if token.box is None:
            raise OcrFailure("OCR token geometry is unavailable")
        left = max(0, round(token.box.x * result.width) - padding_pixels)
        top = max(0, round(token.box.y * result.height) - padding_pixels)
        right = min(result.width, round((token.box.x + token.box.width) * result.width) + padding_pixels)
        bottom = min(result.height, round((token.box.y + token.box.height) * result.height) + padding_pixels)
        draw.rectangle((left, top, max(left, right - 1), max(top, bottom - 1)), fill=fill)
    return result


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _parse_box(row: dict[str, str | None], image_size: tuple[int, int]) -> BoundingBox:
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")
    left = int(row.get("left") or "")
    top = int(row.get("top") or "")
    box_width = int(row.get("width") or "")
    box_height = int(row.get("height") or "")
    if left < 0 or top < 0 or box_width < 0 or box_height < 0:
        raise ValueError("negative OCR geometry")
    if left + box_width > width or top + box_height > height:
        raise ValueError("OCR geometry exceeds the image")
    return BoundingBox(left / width, top / height, box_width / width, box_height / height)
