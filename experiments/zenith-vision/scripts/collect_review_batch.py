from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from zenith_vision import (
    TesseractOcr, XWindowCapture, create_contact_sheet, difference_hash,
    is_distinct, mask_regions, save_batch_manifest, save_review_candidate, select_exact_window,
    structural_privacy_regions,
)

parser = argparse.ArgumentParser()
parser.add_argument("--ui-scale", required=True, choices=("small", "normal", "large", "larger"))
args = parser.parse_args()

maximum_candidates = 12
maximum_seconds = 600
interval_seconds = 10
minimum_hash_distance = 8
started = datetime.now(timezone.utc)
batch_id = started.strftime("batch-%Y%m%dT%H%M%SZ")
batch_directory = Path.home() / ".local/state/zenith-vision/review-batches" / batch_id
batch_directory.mkdir(parents=True, mode=0o700)
accepted_hashes: list[int] = []
entries: list[dict[str, object]] = []
capture = XWindowCapture()
ocr = TesseractOcr()
attempt = 0

deadline = time.monotonic() + maximum_seconds
while len(entries) < maximum_candidates and time.monotonic() < deadline:
    attempt += 1
    target = select_exact_window(
        capture.list_windows(), title="Guild Wars 2",
        instance="steam_app_1284210", window_class="steam_app_1284210",
    )
    frame = capture.capture(target)
    structurally_masked = mask_regions(frame, structural_privacy_regions(args.ui_scale))
    fingerprint = difference_hash(structurally_masked)
    if is_distinct(fingerprint, accepted_hashes, minimum_distance=minimum_hash_distance):
        scan = ocr.scan(frame)
        candidate, receipt, saved = save_review_candidate(
            structurally_masked, batch_directory,
            source_title=target.title, source_instance=target.instance,
            source_class=target.window_class, ocr_token_count=len(scan.tokens),
            mask_policy="operator-trusted-gameplay-v1",
        )
        accepted_hashes.append(fingerprint)
        entries.append({
            "sequence": len(entries) + 1, "candidate": candidate.name,
            "receipt": receipt.name, "candidate_sha256": saved.candidate_sha256,
            "difference_hash": f"{fingerprint:016x}", "ocr_token_count": len(scan.tokens),
        })
        print(json.dumps({"event": "accepted", "attempt": attempt, "count": len(entries)}), flush=True)
    else:
        print(json.dumps({"event": "duplicate_discarded", "attempt": attempt, "count": len(entries)}), flush=True)
    if len(entries) < maximum_candidates:
        time.sleep(interval_seconds)

manifest = save_batch_manifest(
    batch_directory, entries, started_at=started.isoformat(), ui_scale=args.ui_scale,
)
sheet = create_contact_sheet(
    [(f"{entry['sequence']:02d}", batch_directory / str(entry["candidate"])) for entry in entries],
    batch_directory / "contact-sheet.png",
)
print(json.dumps({
    "event": "complete", "batch_id": batch_id, "candidate_count": len(entries),
    "attempts": attempt, "manifest": str(manifest), "contact_sheet": str(sheet),
}, separators=(",", ":")), flush=True)
