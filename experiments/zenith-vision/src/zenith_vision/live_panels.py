from __future__ import annotations

from .capture import WindowIdentity
from .panels import PanelObservation, PanelOcrBackend, scan_panel_titles
from .redaction import mask_regions
from .collection import structural_privacy_regions


class PanelCaptureBackend:
    def capture(self, identity: WindowIdentity): ...


def observe_panels_once(
    capture: PanelCaptureBackend, identity: WindowIdentity, ocr: PanelOcrBackend,
    *, ui_scale: str = "small",
) -> PanelObservation:
    """Observe allowlisted panels once without retaining source or masked pixels."""
    frame = capture.capture(identity)
    try:
        masked = mask_regions(frame, structural_privacy_regions(ui_scale))
    finally:
        frame.close()
    try:
        return scan_panel_titles(masked, ocr)
    finally:
        masked.close()
