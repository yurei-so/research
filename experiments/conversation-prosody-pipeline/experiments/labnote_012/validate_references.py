#!/usr/bin/env python3
"""Validate private PCM reference recordings and freeze their manifest."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import wave

def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

def inspect_wav(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"unsafe or missing reference: {path.name}")
    with wave.open(str(path), "rb") as audio:
        channels, width, rate, frames = (
            audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
        )
    duration = frames / rate
    if channels != 1 or width != 2 or rate not in range(16_000, 48_001):
        raise ValueError(f"{path.name}: expected mono 16-bit PCM at 16-48 kHz")
    if not 1.0 <= duration <= 12.0:
        raise ValueError(f"{path.name}: duration must be 1-12 seconds")
    return {"sha256": digest(path.read_bytes()), "sample_rate": rate,
            "frames": frames, "duration_seconds": round(duration, 6)}

def validate(protocol_path: Path, reference_dir: Path, output: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text())
    if protocol.get("format") != "conversation-prosody.reference-focus-transfer" \
            or protocol.get("version") != 1 or protocol.get("post_processing") != "none":
        raise ValueError("unsupported reference-focus protocol")
    records, seen = [], set()
    for pair in protocol.get("pairs", []):
        if len(pair.get("conditions", [])) != 2:
            raise ValueError("each pair requires exactly two focus conditions")
        for condition in pair["conditions"]:
            name = condition["reference_file"]
            if name in seen or Path(name).name != name or not name.endswith(".wav"):
                raise ValueError("invalid or duplicate reference filename")
            seen.add(name)
            target, focus = pair["target"], condition["focus"]
            if target.casefold().count(focus.casefold()) != 1:
                raise ValueError("focus must occur exactly once in target")
            records.append({"pair_id": pair["pair_id"], "condition_id": condition["condition_id"],
                            "reference_file": name, **inspect_wav(reference_dir / name)})
    if len(records) != 4:
        raise ValueError("protocol must contain exactly four reference recordings")
    manifest = {"format": "conversation-prosody.reference-focus-manifest", "version": 1,
                "protocol_sha256": digest(canonical(protocol)), "references": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    return manifest

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.protocol.resolve(), args.reference_dir.resolve(), args.output.resolve())
    print(canonical({"references": len(result["references"]),
                     "protocol_sha256": result["protocol_sha256"]}))

if __name__ == "__main__":
    main()
