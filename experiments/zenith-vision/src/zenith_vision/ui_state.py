from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Literal

from PIL import Image, ImageFilter, ImageStat


HudRegion = Literal["objectives", "skill_bar", "minimap"]
HudState = Literal["present", "absent", "uncertain"]


@dataclass(frozen=True)
class UiStateFeatures:
    luminance_mean: float
    luminance_stddev: float
    edge_mean: float
    entropy: float

    def vector(self) -> tuple[float, float, float, float]:
        return (self.luminance_mean, self.luminance_stddev, self.edge_mean, self.entropy)


@dataclass(frozen=True)
class UiStateExample:
    region: HudRegion
    state: Literal["present", "absent"]
    features: UiStateFeatures


@dataclass(frozen=True)
class UiStateRecognition:
    format: str
    version: int
    region: HudRegion
    state: HudState
    confidence: float
    source: str


class UiStateBaseline:
    """Small, inspectable baseline for presence/absence experiments.

    This is deliberately an evaluation primitive, not a production detector.
    It abstains when the two class distances are too similar.
    """

    def __init__(self, examples: Iterable[UiStateExample], *, abstain_margin: float = 0.15) -> None:
        if not 0.0 <= abstain_margin < 1.0:
            raise ValueError("abstain margin must be between 0 and 1")
        grouped: dict[tuple[HudRegion, str], list[tuple[float, ...]]] = {}
        for example in examples:
            grouped.setdefault((example.region, example.state), []).append(example.features.vector())
        self._centroids: dict[tuple[HudRegion, str], tuple[float, ...]] = {}
        for key, rows in grouped.items():
            self._centroids[key] = tuple(sum(row[index] for row in rows) / len(rows) for index in range(4))
        self._abstain_margin = abstain_margin

    def recognize(self, image: Image.Image, *, region: HudRegion) -> UiStateRecognition:
        present = self._centroids.get((region, "present"))
        absent = self._centroids.get((region, "absent"))
        if present is None or absent is None:
            raise ValueError(f"region {region!r} requires present and absent training examples")
        vector = extract_ui_state_features(image).vector()
        present_distance = _distance(vector, present)
        absent_distance = _distance(vector, absent)
        total = present_distance + absent_distance
        separation = 0.0 if total == 0.0 else abs(present_distance - absent_distance) / total
        state: HudState = "present" if present_distance < absent_distance else "absent"
        if separation < self._abstain_margin:
            state = "uncertain"
        return UiStateRecognition(
            format="zenith-vision.ui-state", version=1, region=region, state=state,
            confidence=min(1.0, separation), source="feature-centroid-baseline-v1",
        )


def extract_ui_state_features(image: Image.Image) -> UiStateFeatures:
    if image.width < 16 or image.height < 16:
        raise ValueError("UI state crop must be at least 16x16 pixels")
    gray = image.convert("L").resize((96, 96))
    stats = ImageStat.Stat(gray)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return UiStateFeatures(
        luminance_mean=stats.mean[0] / 255.0,
        luminance_stddev=stats.stddev[0] / 255.0,
        edge_mean=ImageStat.Stat(edges).mean[0] / 255.0,
        entropy=gray.entropy() / 8.0,
    )


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))
