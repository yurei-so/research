#!/usr/bin/env python3
"""Generate and acoustically gate a small, audible focus-control pilot."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
from statistics import median
import subprocess
from typing import Any


SAMPLE_RATE = 24_000
VOICES = ("af_heart", "am_adam")
PITCH = 2 ** (1.5 / 12)
GAIN = 10 ** (3.5 / 20)
CROSSFADE_SECONDS = 0.015
PROTOCOL = {
    "format": "conversation-prosody.focus-control-gate",
    "version": 3,
    "source": "labnote-004-oracle-synthesis",
    "selection": "two_minimum_sha256_contrastive_emphasis_pairs",
    "voices": list(VOICES),
    "pitch_semitones": 1.5,
    "gain_db": 3.5,
    "formant": "preserved",
    "pitch_quality": "quality",
    "transients": "smooth",
    "detector": "soft",
    "boundary_crossfade_seconds": CROSSFADE_SECONDS,
    "thresholds": {
        "minimum_local_energy_ratio": 1.08,
        "minimum_local_f0_ratio": 1.05,
        "minimum_relative_waveform_difference": 0.10,
        "maximum_duration_delta_ratio": 0.03,
    },
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def run(command: list[str], *, stdout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, stdout=stdout, stderr=subprocess.PIPE)


def emphasize(source: Path, target: Path, window: tuple[float, float]) -> None:
    start, end = window
    if not 0 <= start < end:
        raise ValueError("invalid focus window")
    fade = CROSSFADE_SECONDS
    overlap = 2 * fade
    graph = (
        f"[0:a]atrim=0:{start + fade},asetpts=PTS-STARTPTS[pre];"
        f"[0:a]atrim={max(0, start - fade)}:{end + fade},asetpts=PTS-STARTPTS,"
        f"rubberband=pitch={PITCH}:tempo=1.0:formant=preserved:pitchq=quality:"
        f"transients=smooth:detector=soft:smoothing=on,volume={GAIN}[focus];"
        f"[0:a]atrim=start={max(0, end - fade)},asetpts=PTS-STARTPTS[post];"
        f"[pre][focus]acrossfade=d={overlap}:c1=qsin:c2=qsin[head];"
        f"[head][post]acrossfade=d={overlap}:c1=qsin:c2=qsin[out]"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(source), "-filter_complex", graph, "-map", "[out]",
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target)])


def decode(path: Path) -> array:
    result = run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                  "-i", str(path), "-f", "s16le", "-ac", "1", "-ar",
                  str(SAMPLE_RATE), "pipe:1"], stdout=subprocess.PIPE)
    samples = array("h")
    samples.frombytes(result.stdout)
    return samples


def segment(samples: array, window: tuple[float, float]) -> array:
    start = max(0, min(len(samples), round(window[0] * SAMPLE_RATE)))
    end = max(start, min(len(samples), round(window[1] * SAMPLE_RATE)))
    return samples[start:end]


def rms(samples: array) -> float:
    return math.sqrt(sum(value * value for value in samples) / max(len(samples), 1))


def median_f0(samples: array) -> float:
    """Estimate voiced F0 with normalized autocorrelation over 40 ms frames."""
    frame_size, hop = 960, 240
    minimum_lag, maximum_lag = 60, 480  # 400 Hz through 50 Hz at 24 kHz
    estimates = []
    for start in range(0, max(0, len(samples) - frame_size + 1), hop):
        frame = samples[start:start + frame_size]
        mean = sum(frame) / frame_size
        centered = [value - mean for value in frame]
        energy = sum(value * value for value in centered)
        if energy < 1:
            continue
        scores = []
        for lag in range(minimum_lag, maximum_lag):
            numerator = sum(centered[index] * centered[index + lag]
                            for index in range(frame_size - lag))
            scores.append(numerator / energy)
        best = max(range(len(scores)), key=scores.__getitem__)
        if scores[best] >= 0.35:
            estimates.append(SAMPLE_RATE / (minimum_lag + best))
    return median(estimates) if estimates else 0.0


def compare(left: Path, right: Path, left_window: tuple[float, float],
            right_window: tuple[float, float]) -> dict[str, Any]:
    a, b = decode(left), decode(right)
    common = min(len(a), len(b))
    difference = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(common)) / max(common, 1))
    baseline = max(rms(a[:common]), rms(b[:common]), 1)
    energy_left = rms(segment(a, left_window)) / max(rms(segment(b, left_window)), 1)
    energy_right = rms(segment(b, right_window)) / max(rms(segment(a, right_window)), 1)
    f0_left = median_f0(segment(a, left_window)) / max(median_f0(segment(b, left_window)), 1e-9)
    f0_right = median_f0(segment(b, right_window)) / max(median_f0(segment(a, right_window)), 1e-9)
    duration_delta = abs(len(a) - len(b)) / max(len(a), len(b), 1)
    metrics = {
        "local_energy_ratio_left": energy_left,
        "local_energy_ratio_right": energy_right,
        "local_f0_ratio_left": f0_left,
        "local_f0_ratio_right": f0_right,
        "relative_waveform_difference": difference / baseline,
        "duration_delta_ratio": duration_delta,
    }
    thresholds = PROTOCOL["thresholds"]
    metrics["passed"] = (
        min(energy_left, energy_right) >= thresholds["minimum_local_energy_ratio"]
        and min(f0_left, f0_right) >= thresholds["minimum_local_f0_ratio"]
        and metrics["relative_waveform_difference"] >= thresholds["minimum_relative_waveform_difference"]
        and duration_delta <= thresholds["maximum_duration_delta_ratio"]
    )
    return metrics


def execute(source_run: Path, output_dir: Path) -> dict[str, Any]:
    corpus = json.loads((source_run / "corpus.json").read_text())
    rows = [json.loads(line) for line in (source_run / "results.jsonl").read_text().splitlines() if line]
    pairs: dict[str, list[dict[str, Any]]] = {}
    for case in corpus:
        if case["phenomenon"] == "contrastive-emphasis":
            pairs.setdefault(case["pair_id"], []).append(case)
    selected = sorted(pairs, key=lambda pair_id: digest(f"labnote-008:{pair_id}"))[:2]
    lookup = {(row["case_id"], row["voice"], row["condition"]): row for row in rows}
    output_dir.mkdir(parents=True, exist_ok=True)
    trials = []
    for pair_id in selected:
        readings = sorted(pairs[pair_id], key=lambda case: case["reading"])
        if len(readings) != 2:
            raise ValueError("invalid contrast pair")
        for voice in VOICES:
            paths, windows = [], []
            neutral_row = lookup[(readings[0]["case_id"], voice, "neutral")]
            neutral = source_run / neutral_row["audio_path"]
            if digest(neutral.read_bytes()) != neutral_row["audio_sha256"]:
                raise ValueError("neutral source digest mismatch")
            for reading in readings:
                gold = lookup[(reading["case_id"], voice, "gold")]
                compiler = gold["compiler"]
                focus = compiler.get("focus_window")
                if not focus:
                    raise ValueError("selected reading lacks a compiled focus window")
                window = (float(focus["start_seconds"]), float(focus["end_seconds"]))
                target = output_dir / "audio" / voice / f"{reading['case_id']}.wav"
                emphasize(neutral, target, window)
                paths.append(target); windows.append(window)
            metrics = compare(paths[0], paths[1], windows[0], windows[1])
            trials.append({
                "trial_id": digest(f"{pair_id}:{voice}")[:24], "pair_id": pair_id,
                "voice": voice, "case_ids": [case["case_id"] for case in readings],
                "focus_spans": [case["gold_ir"]["focus_span"] for case in readings],
                "windows": windows,
                "audio_paths": [str(path.relative_to(output_dir)) for path in paths],
                "audio_sha256": [digest(path.read_bytes()) for path in paths],
                "metrics": metrics,
            })
    report = {
        "format": PROTOCOL["format"], "version": PROTOCOL["version"],
        "protocol_digest": digest(canonical(PROTOCOL)), "protocol": PROTOCOL,
        "source_run": str(source_run), "selected_pairs": selected,
        "trials": trials, "passed_trials": sum(t["metrics"]["passed"] for t in trials),
        "gate_passed": bool(trials) and all(t["metrics"]["passed"] for t in trials),
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args.source_run.resolve(), args.output_dir.resolve())
    print(canonical({"gate_passed": report["gate_passed"],
                     "passed_trials": report["passed_trials"],
                     "trials": len(report["trials"]),
                     "protocol_digest": report["protocol_digest"]}))


if __name__ == "__main__":
    main()
