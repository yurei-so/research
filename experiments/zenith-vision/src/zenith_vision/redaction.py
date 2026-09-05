from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from PIL import Image, ImageDraw

from .models import BoundingBox


@dataclass(frozen=True)
class RevealDecision:
    box: BoundingBox
    classification: Literal["non_sensitive_ui", "game_world"]
    verifier: str
    confidence: float

    def __post_init__(self) -> None:
        if not self.verifier.strip():
            raise ValueError("reveal decisions require a verifier")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class RedactionReceipt:
    width: int
    height: int
    revealed_pixels: int
    total_pixels: int
    decisions_applied: int
    decisions_rejected: int

    @property
    def revealed_fraction(self) -> float:
        return self.revealed_pixels / self.total_pixels if self.total_pixels else 0.0


def reverse_reveal(
    image: Image.Image,
    decisions: Iterable[RevealDecision],
    *,
    minimum_confidence: float = 0.95,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> tuple[Image.Image, RedactionReceipt]:
    """Create a redacted copy and reveal only independently approved regions."""
    if not 0.0 <= minimum_confidence <= 1.0:
        raise ValueError("minimum confidence must be between 0 and 1")
    source = image.convert("RGB")
    output = Image.new("RGB", source.size, fill)
    mask = Image.new("1", source.size, 0)
    draw = ImageDraw.Draw(mask)
    applied = rejected = 0
    for decision in decisions:
        if decision.confidence < minimum_confidence:
            rejected += 1
            continue
        pixels = _pixel_box(decision.box, source.width, source.height)
        output.paste(source.crop(pixels), pixels)
        draw.rectangle((pixels[0], pixels[1], pixels[2] - 1, pixels[3] - 1), fill=1)
        applied += 1
    histogram = mask.histogram()
    revealed = histogram[1] if len(histogram) > 1 else 0
    return output, RedactionReceipt(
        width=source.width, height=source.height, revealed_pixels=revealed,
        total_pixels=source.width * source.height, decisions_applied=applied,
        decisions_rejected=rejected,
    )


def mask_regions(
    image: Image.Image,
    boxes: Iterable[BoundingBox],
    *,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> Image.Image:
    """Mask complete structural privacy zones on a copy of the image."""
    result = image.convert("RGB").copy()
    draw = ImageDraw.Draw(result)
    for box in boxes:
        left, top, right, bottom = _pixel_box(box, result.width, result.height)
        draw.rectangle((left, top, max(left, right - 1), max(top, bottom - 1)), fill=fill)
    return result


def _pixel_box(box: BoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    left = max(0, min(width, round(box.x * width)))
    top = max(0, min(height, round(box.y * height)))
    right = max(left, min(width, round((box.x + box.width) * width)))
    bottom = max(top, min(height, round((box.y + box.height) * height)))
    return left, top, right, bottom
