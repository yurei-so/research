from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


class ManifestError(ValueError):
    """A dataset item is not eligible for experiment intake."""


@dataclass(frozen=True)
class DatasetItem:
    item_id: str
    media_path: str
    media_sha256: str
    source_class: Literal["synthetic", "licensed_public", "private_operator"]
    license: str
    consent: Literal["not_applicable", "explicit"]
    redaction_status: Literal["not_required", "verified"]
    split: Literal["train", "validation", "test"]
    labels_path: str | None = None


@dataclass(frozen=True)
class DatasetManifest:
    name: str
    version: int
    items: tuple[DatasetItem, ...]

    @classmethod
    def load(cls, path: Path) -> "DatasetManifest":
        root = path.resolve().parent
        try:
            raw: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ManifestError(f"cannot read manifest: {error}") from error
        if not isinstance(raw, dict) or raw.get("format") != "zenith-vision.dataset-manifest":
            raise ManifestError("unsupported dataset manifest format")
        if raw.get("version") != 1 or not isinstance(raw.get("name"), str):
            raise ManifestError("manifest requires a name and version 1")
        rows = raw.get("items")
        if not isinstance(rows, list) or not rows:
            raise ManifestError("manifest must contain at least one item")
        items = tuple(_load_item(row, root) for row in rows)
        ids = [item.item_id for item in items]
        if len(ids) != len(set(ids)):
            raise ManifestError("dataset item ids must be unique")
        return cls(name=raw["name"], version=1, items=items)

    def split_counts(self) -> dict[str, int]:
        counts = {"train": 0, "validation": 0, "test": 0}
        for item in self.items:
            counts[item.split] += 1
        return counts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_item(row: Any, root: Path) -> DatasetItem:
    if not isinstance(row, dict):
        raise ManifestError("every dataset item must be an object")
    required = {"id", "media", "sha256", "source_class", "license", "consent", "redaction_status", "split"}
    missing = required - row.keys()
    if missing:
        raise ManifestError(f"dataset item is missing: {', '.join(sorted(missing))}")
    item_id = row["id"]
    if not isinstance(item_id, str) or not item_id or any(char.isspace() for char in item_id):
        raise ManifestError("dataset item id must be a non-empty token")
    source_class = row["source_class"]
    if source_class not in {"synthetic", "licensed_public", "private_operator"}:
        raise ManifestError(f"{item_id}: unsupported source class")
    if row["split"] not in {"train", "validation", "test"}:
        raise ManifestError(f"{item_id}: unsupported split")
    if source_class == "private_operator":
        if row["consent"] != "explicit" or row["redaction_status"] != "verified":
            raise ManifestError(f"{item_id}: private media requires explicit consent and verified redaction")
        if row["license"] != "private-not-for-release":
            raise ManifestError(f"{item_id}: private media must be marked not for release")
    elif row["consent"] != "not_applicable":
        raise ManifestError(f"{item_id}: public or synthetic media must use not_applicable consent")
    media = _safe_relative_path(row["media"], root, item_id)
    if not media.is_file():
        raise ManifestError(f"{item_id}: media file does not exist")
    expected_digest = row["sha256"]
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ManifestError(f"{item_id}: invalid SHA-256 digest")
    if sha256_file(media) != expected_digest.lower():
        raise ManifestError(f"{item_id}: media digest mismatch")
    labels = row.get("labels")
    labels_path = None
    if labels is not None:
        labels_file = _safe_relative_path(labels, root, item_id)
        if not labels_file.is_file():
            raise ManifestError(f"{item_id}: labels file does not exist")
        labels_path = str(labels_file)
    return DatasetItem(
        item_id=item_id, media_path=str(media), media_sha256=expected_digest.lower(),
        source_class=source_class, license=str(row["license"]), consent=row["consent"],
        redaction_status=row["redaction_status"], split=row["split"], labels_path=labels_path,
    )


def _safe_relative_path(value: Any, root: Path, item_id: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{item_id}: path must be a non-empty string")
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root):
        raise ManifestError(f"{item_id}: paths must remain inside the dataset directory")
    return candidate
