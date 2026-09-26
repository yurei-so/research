# SPDX-License-Identifier: AGPL-3.0-only
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "labnote_006"
sys.path.insert(0, str(ROOT))

from dataset_contract import FORMAT, VERSION, canonical_json, sha256_file, validate_manifest


class SpatialDatasetContractTests(unittest.TestCase):
    def test_manifest_requires_digest_bound_split_owned_shards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard = root / "scene-01000.npz"
            shard.write_bytes(b"bounded fixture")
            manifest = {"format": FORMAT, "version": VERSION, "split": "train", "shards": [{
                "path": shard.name, "scene_seed": 1000, "sha256": sha256_file(shard), "bytes": shard.stat().st_size,
            }]}
            self.assertEqual(validate_manifest(manifest, root)["scene_seeds"], [1000])
            shard.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed shard|digest mismatch"):
                validate_manifest(manifest, root)

    def test_split_seed_ranges_cannot_overlap(self):
        manifest = {"format": FORMAT, "version": VERSION, "split": "test", "shards": [{
            "path": "scene-01000.npz", "scene_seed": 1000, "sha256": "0" * 64, "bytes": 1,
        }]}
        with self.assertRaisesRegex(ValueError, "scene seed"):
            validate_manifest(manifest, Path("."), verify_files=False)

    def test_paths_are_relative_and_confined(self):
        manifest = {"format": FORMAT, "version": VERSION, "split": "train", "shards": [{
            "path": "../escape.npz", "scene_seed": 1000, "sha256": "0" * 64, "bytes": 1,
        }]}
        with self.assertRaisesRegex(ValueError, "unsafe shard path"):
            validate_manifest(manifest, Path("."), verify_files=False)

    def test_canonical_manifest_encoding_is_stable(self):
        self.assertEqual(canonical_json({"z": 1, "a": [2]}), '{"a":[2],"z":1}')

    def test_frozen_protocol_binds_dataset_and_claim_boundary(self):
        protocol = json.loads((ROOT / "frozen-protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["status"], "frozen")
        self.assertEqual(protocol["apparatus"]["dataset_set_manifest_sha256"],
                         "fc41ca16c9d6035e3b98c9165ed8ab5b0920c11a040df0500a3e0cd9248eaada")
        self.assertIn("cannot establish mesh reconstruction", protocol["claim_boundary"])

    def test_freezer_help_is_available(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "freeze_dataset.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_completed_result_is_bound_to_runtime_receipt(self):
        result_path = ROOT / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        receipt = json.loads((ROOT / "run-receipt.json").read_text(encoding="utf-8"))
        protocol = json.loads((ROOT / "frozen-protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual(receipt["stderr_bytes"], 0)
        self.assertEqual(receipt["result_sha256"], sha256_file(result_path))
        self.assertEqual(result["dataset_set_manifest_sha256"],
                         protocol["apparatus"]["dataset_set_manifest_sha256"])
        self.assertIsNone(result["dataset_limits"]["test"])
        self.assertLess(result["comparison"]["depth_mae_m"], 0)
        self.assertLess(result["comparison"]["free_space_iou"], 0)
        self.assertGreater(result["comparison"]["discontinuity_f1"], 0)


if __name__ == "__main__":
    unittest.main()
