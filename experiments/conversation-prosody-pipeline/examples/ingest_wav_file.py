from __future__ import annotations

import argparse
import json
import math
import struct
import tempfile
import wave
from pathlib import Path

from conversation_prosody_pipeline import ProsodyPipeline, ingest_wav_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a WAV file with a provided transcript.")
    parser.add_argument("wav_path", nargs="?", help="Path to a PCM WAV file.")
    parser.add_argument(
        "transcript",
        nargs="?",
        default="This is a generated example turn.",
        help="Caller-provided transcript for the WAV file.",
    )
    args = parser.parse_args()

    if args.wav_path is None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "example.wav"
            _write_example_wav(wav_path)
            _print_metadata(wav_path, args.transcript)
        return

    _print_metadata(Path(args.wav_path), args.transcript)


def _print_metadata(wav_path: Path, transcript: str) -> None:
    turn, features = ingest_wav_file(wav_path, transcript)
    metadata = ProsodyPipeline().process_turn(
        transcript=turn.transcript,
        features=features,
        timing=turn.timing,
    )
    print(json.dumps(metadata.to_dict(), indent=2))


def _write_example_wav(path: Path) -> None:
    sample_rate = 8000
    duration_seconds = 1.0
    amplitude = 8000
    frame_count = int(sample_rate * duration_seconds)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frame_count):
            sample = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
            wav_file.writeframesraw(struct.pack("<h", sample))


if __name__ == "__main__":
    main()
