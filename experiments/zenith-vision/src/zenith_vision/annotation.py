from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .layout import DEFAULT_REGION_BOXES
from .models import BoundingBox
from .dataset import DatasetManifest, ManifestError, sha256_file


VISIBLE_HUD_LABELS = ("objectives", "skill_bar", "minimap")


def create_annotation_proposal(
    media: Path,
    output_directory: Path,
    *,
    item_id: str,
    boxes: dict[str, BoundingBox] | None = None,
    now: datetime | None = None,
) -> tuple[Path, Path]:
    """Create a private geometry-seeded label proposal and visual overlay."""
    media = media.resolve()
    output_directory = output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_directory, 0o700)
    digest = hashlib.sha256(media.read_bytes()).hexdigest()
    with Image.open(media) as source:
        overlay = source.convert("RGB").copy()
    draw = ImageDraw.Draw(overlay)
    labels: list[dict[str, object]] = []
    colors = {"objectives": "#ffcc33", "skill_bar": "#39e67a", "minimap": "#4db5ff"}
    selected_boxes = boxes or {kind: DEFAULT_REGION_BOXES[kind] for kind in VISIBLE_HUD_LABELS}
    if set(selected_boxes) != set(VISIBLE_HUD_LABELS):
        raise ValueError("annotation proposal requires exactly the visible HUD labels")
    for kind in VISIBLE_HUD_LABELS:
        box = selected_boxes[kind]
        pixels = (round(box.x * overlay.width), round(box.y * overlay.height),
                  round((box.x + box.width) * overlay.width),
                  round((box.y + box.height) * overlay.height))
        draw.rectangle(pixels, outline=colors[kind], width=max(3, overlay.width // 400))
        draw.rectangle((pixels[0], pixels[1], pixels[0] + 12 + len(kind) * 10, pixels[1] + 24), fill="#000000")
        draw.text((pixels[0] + 5, pixels[1] + 4), kind, fill=colors[kind])
        labels.append({"kind": kind, "box": [box.x, box.y, box.width, box.height]})
    current = now or datetime.now(timezone.utc)
    proposal = {
        "format": "zenith-vision.annotation-proposal", "version": 1,
        "item_id": item_id, "media_sha256": digest,
        "created_at": current.isoformat(),
        "method": "item_specific_seed" if boxes is not None else "gw2_default_layout_baseline",
        "status": "pending_human_review", "labels": labels,
    }
    overlay_path = output_directory / f"{item_id}-overlay.png"
    proposal_path = output_directory / f"{item_id}-proposal.json"
    overlay.save(overlay_path, format="PNG", optimize=True)
    proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    os.chmod(overlay_path, 0o600)
    os.chmod(proposal_path, 0o600)
    return overlay_path, proposal_path


def approve_annotation_proposal(
    dataset_directory: Path,
    proposal_path: Path,
    *,
    item_id: str,
    now: datetime | None = None,
) -> Path:
    """Promote one reviewed proposal into the private dataset label chain."""
    dataset_directory = dataset_directory.resolve()
    proposal_path = proposal_path.resolve()
    manifest_path = dataset_directory / "manifest.json"
    admission_path = dataset_directory / "admissions" / f"{item_id}.json"
    manifest_raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    if proposal.get("format") != "zenith-vision.annotation-proposal" or proposal.get("version") != 1:
        raise ManifestError("unsupported annotation proposal")
    if proposal.get("status") != "pending_human_review" or proposal.get("item_id") != item_id:
        raise ManifestError("annotation proposal is not pending for this item")
    items = [item for item in manifest_raw.get("items", []) if item.get("id") == item_id]
    if len(items) != 1:
        raise ManifestError("dataset item is missing or ambiguous")
    media = dataset_directory / items[0]["media"]
    if sha256_file(media) != proposal.get("media_sha256"):
        raise ManifestError("annotation proposal media digest mismatch")
    kinds = [item.get("kind") for item in proposal.get("labels", [])]
    if kinds != list(VISIBLE_HUD_LABELS):
        raise ManifestError("annotation proposal has unexpected labels")
    for label in proposal["labels"]:
        BoundingBox(*label["box"])
    labels_directory = dataset_directory / "labels"
    labels_directory.mkdir(mode=0o700, exist_ok=True)
    labels_path = labels_directory / f"{item_id}.json"
    current = now or datetime.now(timezone.utc)
    labels_payload = {
        "format": "zenith-vision.region-labels", "version": 1,
        "item_id": item_id, "media_sha256": proposal["media_sha256"],
        "verified_at": current.isoformat(), "source_proposal": proposal_path.name,
        "regions": proposal["labels"],
    }
    _atomic_json(labels_path, labels_payload)
    items[0]["labels"] = str(labels_path.relative_to(dataset_directory))
    _atomic_json(manifest_path, manifest_raw)
    admission["labels_verified"] = True
    admission["labels_verified_at"] = current.isoformat()
    admission["labels_path"] = str(labels_path.relative_to(dataset_directory))
    _atomic_json(admission_path, admission)
    proposal["status"] = "approved"
    proposal["approved_at"] = current.isoformat()
    _atomic_json(proposal_path, proposal)
    DatasetManifest.load(manifest_path)
    return labels_path


def approve_annotation_batch(
    dataset_directory: Path,
    proposals_directory: Path,
    *,
    now: datetime | None = None,
) -> tuple[Path, ...]:
    """Approve exactly one pending proposal for every item in a dataset."""
    dataset_directory = dataset_directory.resolve()
    proposals_directory = proposals_directory.resolve()
    manifest = DatasetManifest.load(dataset_directory / "manifest.json")
    item_ids = tuple(item.item_id for item in manifest.items)
    proposals: dict[str, Path] = {}
    for path in sorted(proposals_directory.glob("*-proposal.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        item_id = raw.get("item_id")
        if not isinstance(item_id, str) or item_id in proposals:
            raise ManifestError("annotation batch contains a missing or duplicate item id")
        proposals[item_id] = path
    if set(proposals) != set(item_ids):
        raise ManifestError("annotation batch must contain exactly one proposal per dataset item")
    current = now or datetime.now(timezone.utc)
    return tuple(
        approve_annotation_proposal(dataset_directory, proposals[item_id], item_id=item_id, now=current)
        for item_id in item_ids
    )


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
