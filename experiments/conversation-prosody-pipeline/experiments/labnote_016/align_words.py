#!/usr/bin/env python3
"""Produce private word timestamps for the frozen Prosody 015 clips."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def align(session_dir: Path, output: Path, model_name: str, compute_type: str) -> dict[str, Any]:
    from faster_whisper import WhisperModel
    bundle = json.loads((session_dir / "annotation-bundle.json").read_text())
    model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
    items = []
    for item in bundle["items"]:
        audio = session_dir / "assets" / item["file_name"]
        if audio.is_symlink() or not audio.is_file() or digest(audio.read_bytes()) != item["sha256"]:
            raise ValueError("source audio integrity failure")
        segments, info = model.transcribe(str(audio), language="en", beam_size=5,
                                          word_timestamps=True, vad_filter=False)
        words = [{"text": word.word.strip(), "start": round(float(word.start), 4),
                  "end": round(float(word.end), 4), "probability": round(float(word.probability), 6)}
                 for segment in segments for word in (segment.words or []) if word.word.strip()]
        if not words:
            raise ValueError("alignment produced no words")
        items.append({"item_id": item["item_id"], "audio_sha256": item["sha256"],
                      "transcript": item["transcript"], "detected_language": info.language,
                      "words": words})
    result = {"format": "conversation-prosody.word-alignments", "version": 1,
              "engine": "faster-whisper", "model": model_name,
              "compute_type": compute_type, "items": items}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()
    result = align(args.session_dir.resolve(), args.output.resolve(), args.model, args.compute_type)
    print(json.dumps({"items": len(result["items"]), "model": result["model"]}, sort_keys=True))


if __name__ == "__main__":
    main()
