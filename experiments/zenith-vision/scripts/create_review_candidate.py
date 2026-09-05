from __future__ import annotations

import json
from pathlib import Path

from zenith_vision import BoundingBox, TesseractOcr, XWindowCapture, mask_regions, save_review_candidate, select_exact_window

capture = XWindowCapture()
target = select_exact_window(
    capture.list_windows(), title="Guild Wars 2",
    instance="steam_app_1284210", window_class="steam_app_1284210",
)
frame = capture.capture(target)
scan = TesseractOcr().scan(frame)
structurally_masked = mask_regions(frame, [
    # Leave a safety gap before the Normal skill-bar proposal at x=0.315.
    BoundingBox(0.0, 0.66, 0.30, 0.34),
    BoundingBox(0.0, 0.0, 0.20, 0.43),
])
candidate, receipt_path, receipt = save_review_candidate(
    structurally_masked, Path.home() / ".local/state/zenith-vision/review",
    source_title=target.title, source_instance=target.instance,
    source_class=target.window_class, ocr_token_count=len(scan.tokens),
    mask_policy="operator-trusted-gameplay-v1",
)
print(json.dumps({
    "format": receipt.format, "version": receipt.version, "status": "pending_human_review",
    "candidate": str(candidate), "receipt": str(receipt_path),
    "width": receipt.width, "height": receipt.height,
    "ocr_token_count": receipt.ocr_token_count, "mask_policy": receipt.mask_policy,
    "dataset_admitted": receipt.dataset_admitted,
}, separators=(",", ":")))
