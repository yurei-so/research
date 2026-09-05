#!/usr/bin/env python3
"""Download, exercise, and fingerprint Kokoro before offline synthesis."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from kokoro import KPipeline


MODEL_CACHE = Path.home() / ".cache" / "huggingface" / "hub" / "models--hexgrad--Kokoro-82M"
VOICES = ("af_heart", "am_adam")
SAMPLE_RATE = 24_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def versions() -> dict[str, str]:
    result = {}
    for name in ("kokoro", "misaki", "numpy", "soundfile", "torch", "huggingface-hub"):
        result[name] = importlib.metadata.version(name)
    return result


def cache_inventory() -> list[dict[str, Any]]:
    inventory = []
    if not MODEL_CACHE.exists():
        return inventory
    for path in sorted(MODEL_CACHE.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        inventory.append({
            "path": str(path.relative_to(MODEL_CACHE)),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    for path in sorted(MODEL_CACHE.rglob("*")):
        if path.is_symlink():
            resolved = path.resolve()
            inventory.append({
                "path": str(path.relative_to(MODEL_CACHE)),
                "symlink_target": os.path.relpath(resolved, MODEL_CACHE),
                "size": resolved.stat().st_size,
                "sha256": sha256_file(resolved),
            })
    return inventory


def main() -> int:
    root = Path("artifacts/labnote-004/kokoro-preflight").resolve()
    root.mkdir(parents=True, exist_ok=True)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    warmups = []
    for voice in VOICES:
        chunks = []
        for _, _, audio in pipeline(
            "The same words can carry a different meaning.", voice=voice, speed=1.0
        ):
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            chunks.append(np.asarray(audio, dtype=np.float32).reshape(-1))
        if not chunks:
            raise RuntimeError(f"Kokoro produced no warm-up audio for {voice}")
        combined = np.concatenate(chunks)
        output = root / f"{voice}.wav"
        sf.write(output, combined, SAMPLE_RATE, subtype="PCM_16")
        warmups.append({
            "voice": voice,
            "path": output.name,
            "samples": len(combined),
            "sha256": sha256_file(output),
        })
    manifest = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "model_repo": "hexgrad/Kokoro-82M",
        "device": "cpu",
        "packages": versions(),
        "cache_inventory": cache_inventory(),
        "warmups": warmups,
    }
    temporary = root / "manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, root / "manifest.json")
    print(json.dumps({
        "manifest": str(root / "manifest.json"),
        "cache_files": len(manifest["cache_inventory"]),
        "warmups": warmups,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
