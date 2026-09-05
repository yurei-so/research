from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image


PanelEvidenceKind = Literal["hero", "inventory"]
TileKind = Literal["left", "center"]


@dataclass(frozen=True)
class PanelRegion:
    evidence: PanelEvidenceKind
    tile: TileKind
    index: int
    box: tuple[float, float, float, float]

    @property
    def region_id(self) -> str:
        return f"{self.evidence}:{self.tile}:{self.index:02d}"


def panel_region_plan() -> tuple[PanelRegion, ...]:
    """Return a fixed, inspectable Small-UI panel evidence plan.

    Hero proposals cover title/header and vertical icon-rail structures near
    the upper half of either overlapping search tile. Inventory proposals
    cover tall item-grid structures. The plan is fixed before evaluation and
    does not inspect labels or holdout pixels.
    """
    regions: list[PanelRegion] = []
    for tile in ("left", "center"):
        hero_boxes = (
            (0.18, 0.00, 0.62, 0.24),
            (0.38, 0.00, 0.82, 0.24),
            (0.56, 0.00, 1.00, 0.24),
            (0.30, 0.02, 0.70, 0.50),
            (0.56, 0.02, 0.96, 0.50),
        )
        inventory_boxes = (
            (0.00, 0.08, 0.42, 0.90),
            (0.18, 0.08, 0.60, 0.90),
            (0.38, 0.08, 0.80, 0.90),
            (0.58, 0.08, 1.00, 0.90),
        )
        regions.extend(PanelRegion("hero", tile, index, box) for index, box in enumerate(hero_boxes))
        regions.extend(PanelRegion("inventory", tile, index, box) for index, box in enumerate(inventory_boxes))
    return tuple(regions)


def crop_panel_regions(
    left: Image.Image, center: Image.Image, *, evidence: PanelEvidenceKind,
) -> tuple[tuple[PanelRegion, Image.Image], ...]:
    sources = {"left": left, "center": center}
    crops: list[tuple[PanelRegion, Image.Image]] = []
    for region in panel_region_plan():
        if region.evidence != evidence:
            continue
        source = sources[region.tile]
        x1, y1, x2, y2 = region.box
        crops.append((region, source.crop((round(source.width * x1), round(source.height * y1),
                                           round(source.width * x2), round(source.height * y2)))))
    return tuple(crops)
