from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .dataset import DatasetManifest, ManifestError, sha256_file


def admit_review_candidate(
    candidate: Path,
    receipt_path: Path,
    dataset_directory: Path,
    *,
    item_id: str,
    now: datetime | None = None,
) -> Path:
    """Admit one reviewed candidate to a new private, non-release holdout dataset."""
    candidate = candidate.resolve()
    receipt_path = receipt_path.resolve()
    dataset_directory = dataset_directory.resolve()
    if dataset_directory.exists() and any(dataset_directory.iterdir()):
        raise FileExistsError("dataset admission target must be empty")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read review receipt: {error}") from error
    if receipt.get("format") != "zenith-vision.review-candidate" or receipt.get("version") != 2:
        raise ManifestError("unsupported review receipt")
    if receipt.get("dataset_admitted") is not False:
        raise ManifestError("review candidate is already admitted")
    digest = sha256_file(candidate)
    if digest != receipt.get("candidate_sha256"):
        raise ManifestError("review candidate digest mismatch")
    if receipt.get("mask_policy") != "operator-trusted-gameplay-v1":
        raise ManifestError("review candidate mask policy is not approved for this dataset")

    media = dataset_directory / "media" / f"{item_id}.png"
    admissions = dataset_directory / "admissions"
    media.parent.mkdir(parents=True, mode=0o700, exist_ok=False)
    admissions.mkdir(mode=0o700)
    shutil.copyfile(candidate, media)
    os.chmod(media, 0o600)
    current = now or datetime.now(timezone.utc)
    admission = {
        "format": "zenith-vision.dataset-admission", "version": 1,
        "item_id": item_id, "admitted_at": current.isoformat(),
        "candidate_sha256": digest, "review_receipt": receipt_path.name,
        "consent": "explicit", "redaction_status": "verified",
        "license": "private-not-for-release", "labels_verified": False,
    }
    admission_path = admissions / f"{item_id}.json"
    admission_path.write_text(json.dumps(admission, indent=2) + "\n", encoding="utf-8")
    os.chmod(admission_path, 0o600)
    manifest_path = dataset_directory / "manifest.json"
    manifest_path.write_text(json.dumps({
        "format": "zenith-vision.dataset-manifest", "version": 1,
        "name": "operator-pilot-v1", "items": [{
            "id": item_id, "media": str(media.relative_to(dataset_directory)),
            "sha256": digest, "source_class": "private_operator",
            "license": "private-not-for-release", "consent": "explicit",
            "redaction_status": "verified", "split": "test",
        }],
    }, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    os.chmod(dataset_directory, 0o700)
    DatasetManifest.load(manifest_path)

    receipt["dataset_admitted"] = True
    receipt["dataset_name"] = "operator-pilot-v1"
    receipt["dataset_item_id"] = item_id
    receipt["admitted_at"] = current.isoformat()
    temporary = receipt_path.with_name(f".{receipt_path.name}.tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, receipt_path)
    return manifest_path


def admit_review_batch(
    batch_directory: Path,
    dataset_directory: Path,
    *,
    dataset_name: str = "operator-holdout-v1",
    ui_scale: str | None = None,
) -> Path:
    """Admit one approved review batch as an unlabeled private test holdout."""
    batch_directory = batch_directory.resolve()
    dataset_directory = dataset_directory.resolve()
    if dataset_directory.exists() and any(dataset_directory.iterdir()):
        raise FileExistsError("batch admission target must be empty")
    batch_path = batch_directory / "batch.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if batch.get("format") != "zenith-vision.review-batch" or batch.get("version") != 1:
        raise ManifestError("unsupported review batch")
    if batch.get("status") != "pending_human_review":
        raise ManifestError("review batch is not pending human review")
    captured_ui_scale = batch.get("ui_scale")
    if captured_ui_scale is not None and captured_ui_scale != ui_scale:
        raise ManifestError("review batch UI scale does not match dataset provenance")
    entries = batch.get("candidates")
    if not isinstance(entries, list) or not entries or len(entries) > 100:
        raise ManifestError("review batch candidate count is invalid")
    media_directory = dataset_directory / "media"
    admissions_directory = dataset_directory / "admissions"
    media_directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    admissions_directory.mkdir(mode=0o700)
    manifest_items: list[dict[str, object]] = []
    updates: list[tuple[Path, dict[str, object]]] = []
    now = datetime.now(timezone.utc).isoformat()
    for index, entry in enumerate(entries, start=1):
        item_id = f"holdout-{index:05d}"
        candidate = batch_directory / str(entry.get("candidate"))
        receipt_path = batch_directory / str(entry.get("receipt"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        digest = sha256_file(candidate)
        if digest != entry.get("candidate_sha256") or digest != receipt.get("candidate_sha256"):
            raise ManifestError(f"{item_id}: candidate digest mismatch")
        if receipt.get("dataset_admitted") is not False:
            raise ManifestError(f"{item_id}: candidate is already admitted")
        if receipt.get("mask_policy") != "operator-trusted-gameplay-v1":
            raise ManifestError(f"{item_id}: mask policy is not approved")
        destination = media_directory / f"{item_id}.png"
        shutil.copyfile(candidate, destination)
        os.chmod(destination, 0o600)
        admission = {
            "format": "zenith-vision.dataset-admission", "version": 1,
            "item_id": item_id, "admitted_at": now, "candidate_sha256": digest,
            "review_receipt": receipt_path.name, "consent": "explicit",
            "redaction_status": "verified", "license": "private-not-for-release",
            "labels_verified": False, "ui_scale": ui_scale,
        }
        _write_private_json(admissions_directory / f"{item_id}.json", admission)
        manifest_items.append({
            "id": item_id, "media": str(destination.relative_to(dataset_directory)),
            "sha256": digest, "source_class": "private_operator",
            "license": "private-not-for-release", "consent": "explicit",
            "redaction_status": "verified", "split": "test",
        })
        receipt["dataset_admitted"] = True
        receipt["dataset_name"] = dataset_name
        receipt["dataset_item_id"] = item_id
        receipt["admitted_at"] = now
        updates.append((receipt_path, receipt))
    manifest_path = dataset_directory / "manifest.json"
    _write_private_json(manifest_path, {
        "format": "zenith-vision.dataset-manifest", "version": 1,
        "name": dataset_name, "ui_scale": ui_scale, "items": manifest_items,
    })
    os.chmod(dataset_directory, 0o700)
    DatasetManifest.load(manifest_path)
    for path, receipt in updates:
        _write_private_json(path, receipt)
    batch["status"] = "approved"
    batch["admitted_at"] = now
    batch["dataset_name"] = dataset_name
    batch["ui_scale"] = ui_scale
    _write_private_json(batch_path, batch)
    return manifest_path


def _write_private_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
