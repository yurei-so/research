from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class HybridPanelDecision:
    panels: frozenset[str]
    source: str


def combine_panel_evidence(
    title_panels: frozenset[str], visual_scores: Mapping[str, float],
) -> HybridPanelDecision:
    """Conservatively combine high-precision titles with structural vision scores."""
    required = {"hero", "inventory"}
    if set(visual_scores) != required:
        raise ValueError("visual scores must contain exactly hero and inventory")
    if any(not 0.0 <= score <= 1.0 for score in visual_scores.values()):
        raise ValueError("visual scores must be between 0 and 1")
    if not title_panels.issubset(required):
        raise ValueError("unsupported title panel")
    panels = set(title_panels)
    if visual_scores["hero"] >= 0.80:
        panels.add("hero")
    if visual_scores["inventory"] >= 0.55:
        panels.add("inventory")
    return HybridPanelDecision(
        frozenset(panels),
        "title_plus_structural" if title_panels else "structural_high_confidence" if panels else "abstained",
    )
