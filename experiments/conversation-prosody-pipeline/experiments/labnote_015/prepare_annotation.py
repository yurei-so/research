#!/usr/bin/env python3
"""Prepare a blinded, owner-local annotation bundle from Prosody 014."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def write_private(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def prepare(protocol_path: Path, source_dir: Path, output_dir: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text())
    report = json.loads((source_dir / "report.json").read_text())
    if report.get("format") != protocol.get("source_format"):
        raise ValueError("unexpected source report format")
    trials = report.get("trials", [])
    if not report.get("integrity_gate_passed") or len(trials) != protocol["expected_items"]:
        raise ValueError("annotation requires a complete passing source run")
    source_digest = digest(canonical(report))
    ordered = list(trials)
    random.Random(int(source_digest[:16], 16)).shuffle(ordered)

    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets_dir.chmod(0o700)
    items, reveal = [], []
    for index, trial in enumerate(ordered):
        source = source_dir / trial["audio_path"]
        if source.is_symlink() or not source.is_file():
            raise ValueError("source audio must be a regular non-symlink file")
        content = source.read_bytes()
        if digest(content) != trial["audio_sha256"]:
            raise ValueError("source audio digest mismatch")
        item_id = digest(f"prosody-015:{source_digest}:{trial['trial_id']}")[:24]
        file_name = f"clip-{index + 1:02d}.wav"
        destination = assets_dir / file_name
        shutil.copyfile(source, destination)
        destination.chmod(0o600)
        items.append({"item_id": item_id, "ordinal": index + 1,
                      "transcript": trial["target"], "file_name": file_name,
                      "sha256": trial["audio_sha256"]})
        reveal_fields = protocol.get("reveal_fields", protocol["blind_fields"])
        reveal.append({"item_id": item_id, **{
            key: trial[key] for key in reveal_fields}})
    bundle = {"format": protocol["format"], "version": 1,
              "source_report_sha256": source_digest,
              "protocol_sha256": digest(canonical(protocol)),
              "title": protocol.get("title", "What did the voice actually do?"),
              "speech_acts": protocol["speech_acts"], "affects": protocol["affects"],
              "score_range": protocol["score_range"], "items": items}
    key = {"format": "conversation-prosody.emergent-reading-annotation-key",
           "version": 1, "bundle_sha256": digest(canonical(bundle)), "items": reveal}
    write_private(output_dir / "annotation-bundle.json", bundle)
    write_private(output_dir / "annotation-key.json", key)
    return {"items": len(items), "bundle_sha256": key["bundle_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(canonical(prepare(args.protocol.resolve(), args.source_dir.resolve(),
                            args.output_dir.resolve())))


if __name__ == "__main__":
    main()
