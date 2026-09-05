from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import DatasetManifest, ManifestError


class DatasetManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media = self.root / "fixture.bin"
        self.media.write_bytes(b"synthetic fixture")
        self.digest = hashlib.sha256(self.media.read_bytes()).hexdigest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def manifest(self, **overrides: object) -> Path:
        item: dict[str, object] = {
            "id": "fixture-001", "media": "fixture.bin", "sha256": self.digest,
            "source_class": "synthetic", "license": "CC0-1.0",
            "consent": "not_applicable", "redaction_status": "not_required", "split": "test",
        }
        item.update(overrides)
        path = self.root / "manifest.json"
        path.write_text(json.dumps({"format": "zenith-vision.dataset-manifest", "version": 1,
                                    "name": "fixture", "items": [item]}), encoding="utf-8")
        return path

    def test_loads_digest_bound_synthetic_item(self) -> None:
        loaded = DatasetManifest.load(self.manifest())
        self.assertEqual(loaded.split_counts(), {"train": 0, "validation": 0, "test": 1})

    def test_rejects_changed_media(self) -> None:
        path = self.manifest()
        self.media.write_bytes(b"changed")
        with self.assertRaisesRegex(ManifestError, "digest mismatch"):
            DatasetManifest.load(path)

    def test_private_media_requires_consent_and_verified_redaction(self) -> None:
        path = self.manifest(source_class="private_operator", license="private-not-for-release",
                             consent="not_applicable", redaction_status="verified")
        with self.assertRaisesRegex(ManifestError, "explicit consent"):
            DatasetManifest.load(path)

    def test_rejects_path_escape(self) -> None:
        with self.assertRaisesRegex(ManifestError, "inside the dataset directory"):
            DatasetManifest.load(self.manifest(media="../outside.bin"))

    def test_rejects_duplicate_ids(self) -> None:
        path = self.manifest()
        raw = json.loads(path.read_text())
        raw["items"].append(dict(raw["items"][0]))
        path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ManifestError, "ids must be unique"):
            DatasetManifest.load(path)


if __name__ == "__main__":
    unittest.main()
