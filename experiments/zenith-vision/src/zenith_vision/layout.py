from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import BoundingBox


@dataclass(frozen=True)
class RegionProposal:
    kind: str
    box: BoundingBox
    confidence: float
    source: str = "gw2_default_layout_baseline"


@dataclass(frozen=True)
class RegionLabel:
    kind: str
    box: BoundingBox


@dataclass(frozen=True)
class RegionMetrics:
    matched: int
    expected: int
    proposed: int
    mean_iou: float
    recall_at_50: float


# Conservative normalized crops for the default GW2 HUD. They are crop
# proposals, not semantic detections, and deliberately avoid the center view.
DEFAULT_REGION_BOXES: dict[str, BoundingBox] = {
    "player_status": BoundingBox(0.000, 0.000, 0.300, 0.180),
    "objectives": BoundingBox(0.690, 0.035, 0.310, 0.410),
    "chat": BoundingBox(0.000, 0.675, 0.330, 0.325),
    "skill_bar": BoundingBox(0.315, 0.750, 0.420, 0.250),
    "minimap": BoundingBox(0.735, 0.680, 0.265, 0.320),
}

# Frozen after operator review of the three calibration strata in Labnote 003.
# These remain crop heuristics and must not be described as semantic detections.
UI_PROFILE_REGION_BOXES: dict[str, dict[str, BoundingBox]] = {
    "small": {
        "objectives": BoundingBox(0.855, 0.000, 0.145, 0.360),
        "skill_bar": BoundingBox(0.349, 0.877, 0.379, 0.123),
        "minimap": BoundingBox(0.831, 0.771, 0.169, 0.228),
    },
    "normal": {
        "objectives": BoundingBox(0.840, 0.000, 0.160, 0.540),
        "skill_bar": BoundingBox(0.300, 0.840, 0.400, 0.160),
        "minimap": BoundingBox(0.810, 0.740, 0.190, 0.260),
    },
    "large": {
        "objectives": BoundingBox(0.830, 0.000, 0.170, 0.550),
        "skill_bar": BoundingBox(0.300, 0.840, 0.430, 0.160),
        "minimap": BoundingBox(0.790, 0.700, 0.210, 0.300),
    },
}


def propose_default_regions(width: int, height: int) -> tuple[RegionProposal, ...]:
    _validate_viewport(width, height)
    return tuple(RegionProposal(kind, box, 0.5) for kind, box in DEFAULT_REGION_BOXES.items())


def propose_profile_regions(width: int, height: int, *, ui_scale: str) -> tuple[RegionProposal, ...]:
    _validate_viewport(width, height)
    boxes = UI_PROFILE_REGION_BOXES.get(ui_scale)
    if boxes is None:
        raise ValueError("unsupported UI scale")
    return tuple(
        RegionProposal(kind, box, 0.75, source=f"gw2_{ui_scale}_layout_profile_v1")
        for kind, box in boxes.items()
    )


def _validate_viewport(width: int, height: int) -> None:
    if width < 640 or height < 480:
        raise ValueError("viewport must be at least 640x480")
    if width / height < 4 / 3:
        raise ValueError("unsupported viewport aspect ratio")


def intersection_over_union(left: BoundingBox, right: BoundingBox) -> float:
    x1, y1 = max(left.x, right.x), max(left.y, right.y)
    x2 = min(left.x + left.width, right.x + right.width)
    y2 = min(left.y + left.height, right.y + right.height)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = left.width * left.height + right.width * right.height - intersection
    return intersection / union if union else 0.0


def evaluate_regions(
    proposals: Iterable[RegionProposal], labels: Iterable[RegionLabel], *, threshold: float = 0.5
) -> RegionMetrics:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    proposed = tuple(proposals)
    expected = tuple(labels)
    scores: list[float] = []
    matched = 0
    for label in expected:
        candidates = [intersection_over_union(label.box, item.box) for item in proposed if item.kind == label.kind]
        score = max(candidates, default=0.0)
        scores.append(score)
        matched += score >= threshold
    return RegionMetrics(
        matched=matched, expected=len(expected), proposed=len(proposed),
        mean_iou=sum(scores) / len(scores) if scores else 0.0,
        recall_at_50=matched / len(expected) if expected else 0.0,
    )
