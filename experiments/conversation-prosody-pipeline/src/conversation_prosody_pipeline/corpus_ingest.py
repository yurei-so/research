"""Local, dependency-free corpus experiments over caller-provided WAV transcripts."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
from typing import Iterable, Sequence

from conversation_prosody_pipeline.audio_file import ingest_wav_file
from conversation_prosody_pipeline.audio_stream import ingest_wav_stream
from conversation_prosody_pipeline.types import TurnFeatures


DEFAULT_JSONL = Path("import") / "outputs" / "corpus_metadata.jsonl"
DEFAULT_CSV = Path("import") / "reports" / "corpus_summary.csv"
FEATURE_NAMES = ("duration_ms", "energy_rms", "speech_rate_wpm")


class CorpusInputError(ValueError):
    """An actionable problem with the selected corpus input."""


@dataclass(frozen=True)
class CorpusPair:
    wav_path: Path
    transcript_path: Path
    transcript: str


@dataclass(frozen=True)
class DiscoveryResult:
    pairs: list[CorpusPair]
    wav_count: int
    flac_count: int
    missing_transcripts: list[Path]


def _read_manifest(path: Path) -> dict[str, str]:
    transcripts: dict[str, str] = {}
    with path.open(encoding="utf-8") as source:
        for raw_line in source:
            utterance_id, separator, transcript = raw_line.strip().partition(" ")
            if separator and transcript.strip():
                transcripts[utterance_id] = transcript.strip()
    return transcripts


def discover_pairs(input_dir: str | Path, limit: int | None = None) -> DiscoveryResult:
    """Find WAVs with either same-stem sidecars or LibriSpeech manifests."""

    root = Path(input_dir)
    if not root.is_dir():
        raise CorpusInputError(f"input directory does not exist: {root}")
    if limit is not None and limit < 1:
        raise CorpusInputError("--limit must be greater than zero")

    wav_paths = sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".wav"
    )
    flac_count = sum(
        1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".flac"
    )
    manifests: dict[Path, tuple[Path, dict[str, str]]] = {}
    for manifest_path in sorted(root.rglob("*.trans.txt")):
        manifests[manifest_path.parent] = (manifest_path, _read_manifest(manifest_path))

    pairs: list[CorpusPair] = []
    missing: list[Path] = []
    for wav_path in wav_paths:
        sidecar = wav_path.with_suffix(".txt")
        transcript_path: Path | None = None
        transcript: str | None = None
        if sidecar.is_file():
            transcript_path = sidecar
            transcript = sidecar.read_text(encoding="utf-8").strip()
        elif wav_path.parent in manifests:
            manifest_path, chapter_transcripts = manifests[wav_path.parent]
            transcript_path = manifest_path
            transcript = chapter_transcripts.get(wav_path.stem)

        if transcript_path is None or not transcript:
            missing.append(wav_path)
            continue
        if limit is None or len(pairs) < limit:
            pairs.append(CorpusPair(wav_path, transcript_path, transcript))

    return DiscoveryResult(pairs, len(wav_paths), flac_count, missing)


def _feature_dict(features: TurnFeatures) -> dict[str, float | None]:
    return {name: getattr(features, name) for name in FEATURE_NAMES}


def _same(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-6)


def ingest_pair(pair: CorpusPair, mode: str, chunk_duration_ms: float) -> dict[str, object]:
    result: dict[str, object] = {
        "audio_path": str(pair.wav_path),
        "transcript_path": str(pair.transcript_path),
        "transcript": pair.transcript,
    }
    modes: dict[str, object] = {}
    if mode in {"file", "both"}:
        turn, features = ingest_wav_file(pair.wav_path, pair.transcript)
        modes["file"] = {"source": turn.metadata["source"], "features": _feature_dict(features)}
    if mode in {"stream", "both"}:
        turn, features = ingest_wav_stream(
            pair.wav_path, pair.transcript, chunk_duration_ms=chunk_duration_ms
        )
        modes["stream"] = {
            "source": turn.metadata["source"],
            "chunk_count": turn.metadata["chunk_count"],
            "chunk_duration_ms": chunk_duration_ms,
            "features": _feature_dict(features),
        }
    result["modes"] = modes

    if mode == "both":
        file_features = modes["file"]["features"]
        stream_features = modes["stream"]["features"]
        comparisons = {
            name: {
                "file": file_features[name],
                "stream": stream_features[name],
                "match": _same(file_features[name], stream_features[name]),
            }
            for name in FEATURE_NAMES
        }
        result["comparison"] = comparisons
        result["features_match"] = all(item["match"] for item in comparisons.values())
    return result


def write_jsonl(path: str | Path, records: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, sort_keys=True) + "\n")


def write_summary_csv(path: str | Path, records: Sequence[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "audio_path", "transcript_path", "mode", "duration_ms", "energy_rms",
        "speech_rate_wpm", "features_match",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            for mode, mode_result in record["modes"].items():
                writer.writerow(
                    {
                        "audio_path": record["audio_path"],
                        "transcript_path": record["transcript_path"],
                        "mode": mode,
                        **mode_result["features"],
                        "features_match": record.get("features_match", ""),
                    }
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="directory containing WAV audio")
    parser.add_argument("--limit", type=int, help="maximum number of pairs to process")
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--mode", choices=("file", "stream", "both"), default="both")
    parser.add_argument("--chunk-duration-ms", type=float, default=100.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.chunk_duration_ms <= 0:
            raise CorpusInputError("--chunk-duration-ms must be greater than zero")
        discovery = discover_pairs(args.input_dir, args.limit)
        if not discovery.pairs:
            if discovery.wav_count == 0 and discovery.flac_count:
                raise CorpusInputError(
                    f"found {discovery.flac_count} FLAC files but no WAV files in {args.input_dir}; "
                    "convert the corpus to PCM WAV in a separate ignored output directory, then "
                    "run this command on that directory (this repository has no FLAC converter)"
                )
            raise CorpusInputError(
                f"found {discovery.wav_count} WAV files but no WAV/transcript pairs in "
                f"{args.input_dir}; add same-stem .txt sidecars or LibriSpeech *.trans.txt manifests"
            )
    except CorpusInputError as error:
        print(f"corpus ingest: {error}", file=sys.stderr)
        return 2

    records = [ingest_pair(pair, args.mode, args.chunk_duration_ms) for pair in discovery.pairs]
    write_jsonl(args.output_jsonl, records)
    write_summary_csv(args.summary_csv, records)
    mismatches = sum(record.get("features_match") is False for record in records)
    print(
        f"corpus ingest: processed {len(records)} pair(s) in {args.mode} mode; "
        f"{len(discovery.missing_transcripts)} WAV(s) skipped without transcripts"
    )
    if args.mode == "both":
        print(f"file/stream comparison: {len(records) - mismatches} matched, {mismatches} mismatched")
    print(f"JSONL: {args.output_jsonl}")
    print(f"CSV: {args.summary_csv}")
    return 1 if mismatches else 0
