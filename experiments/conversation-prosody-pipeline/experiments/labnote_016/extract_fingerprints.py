#!/usr/bin/env python3
"""Extract deterministic acoustic fingerprints and evaluate frozen Prosody 015 labels."""
from __future__ import annotations

import argparse
from itertools import combinations
import json
import math
from pathlib import Path
import re
from statistics import mean, median
from typing import Any
import wave

import numpy as np


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("expected mono PCM16 WAV")
        rate = wav.getframerate()
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    return data, rate


def frames(audio: np.ndarray, size: int, hop: int) -> list[tuple[int, np.ndarray]]:
    return [(start, audio[start:start + size]) for start in range(0, max(0, len(audio) - size + 1), hop)]


def f0(frame: np.ndarray, rate: int, low: float, high: float) -> float | None:
    centered = frame - np.mean(frame)
    energy = float(np.dot(centered, centered))
    if energy < 1e-8:
        return None
    correlation = np.correlate(centered, centered, mode="full")[len(centered) - 1:]
    lo, hi = max(1, int(rate / high)), min(len(correlation) - 1, int(rate / low))
    if hi <= lo:
        return None
    lag = lo + int(np.argmax(correlation[lo:hi + 1]))
    if correlation[lag] < 0.3 * correlation[0]:
        return None
    return rate / lag


def standardize(values: list[float]) -> list[float]:
    center = mean(values)
    scale = math.sqrt(mean([(value - center) ** 2 for value in values]))
    return [(value - center) / scale if scale > 1e-12 else 0.0 for value in values]


def clip_features(audio: np.ndarray, rate: int, protocol: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, float]]]:
    config = protocol["frames"]
    window, hop = round(rate * config["window_ms"] / 1000), round(rate * config["hop_ms"] / 1000)
    rows = []
    for start, frame in frames(audio, window, hop):
        rms = math.sqrt(float(np.mean(frame * frame)))
        rows.append({"time": (start + window / 2) / rate, "rms": rms,
                     "f0": f0(frame, rate, config["pitch_min_hz"], config["pitch_max_hz"])})
    levels = np.asarray([row["rms"] for row in rows])
    threshold = max(0.003, float(np.percentile(levels, 25)) * 1.8) if len(levels) else 0.003
    voiced = [row for row in rows if row["rms"] > threshold]
    pitches = [row["f0"] for row in voiced if row["f0"] is not None]
    quiet = [row["rms"] <= threshold for row in rows]
    pauses, start = [], None
    for index, value in enumerate(quiet):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(quiet) - 1):
            end = index if not value else index + 1
            duration = (end - start) * config["hop_ms"] / 1000
            if duration >= 0.15 and start > 0 and end < len(quiet):
                pauses.append(duration)
            start = None
    duration = len(audio) / rate
    thirds = [(duration * i / 3, duration * (i + 1) / 3) for i in range(3)]
    energy_thirds = [20 * math.log10(max(1e-9, mean([r["rms"] for r in voiced if a <= r["time"] < b])
                                                   if any(a <= r["time"] < b for r in voiced) else 1e-9))
                     for a, b in thirds]
    f0_thirds = [median([r["f0"] for r in voiced if r["f0"] is not None and a <= r["time"] < b])
                 if any(r["f0"] is not None and a <= r["time"] < b for r in voiced) else 0.0
                 for a, b in thirds]
    slope = float(np.polyfit([r["time"] for r in voiced if r["f0"] is not None], pitches, 1)[0]) if len(pitches) >= 2 else 0.0
    features = {"duration_seconds": duration, "voiced_fraction": len(voiced) / max(1, len(rows)),
                "internal_pause_count": len(pauses),
                "energy_variability": float(np.std([r["rms"] for r in voiced]) / max(1e-9, mean([r["rms"] for r in voiced]))) if voiced else 0.0,
                "f0_median_hz": median(pitches) if pitches else 0.0,
                "f0_std_hz": float(np.std(pitches)) if pitches else 0.0,
                "f0_range_hz": float(np.percentile(pitches, 90) - np.percentile(pitches, 10)) if pitches else 0.0,
                "f0_slope_hz_per_second": slope, "energy_thirds_db": energy_thirds, "f0_thirds_hz": f0_thirds}
    return features, rows


def word_prominence(audio: np.ndarray, rate: int, words: list[dict[str, Any]], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = []
    previous_end = 0.0
    for word in words:
        start, end = max(0.0, float(word["start"])), min(len(audio) / rate, float(word["end"]))
        segment = audio[round(start * rate):round(end * rate)]
        pitch_values = [f0(frame, rate, protocol["frames"]["pitch_min_hz"], protocol["frames"]["pitch_max_hz"])
                        for _, frame in frames(segment, round(rate * 0.025), round(rate * 0.010))]
        pitch_values = [value for value in pitch_values if value is not None]
        rms = math.sqrt(float(np.mean(segment * segment))) if len(segment) else 0.0
        metrics.append({"word": word["text"], "start": start, "end": end,
                        "energy_db": 20 * math.log10(max(rms, 1e-9)), "duration_seconds": max(0.0, end - start),
                        "f0_median_hz": median(pitch_values) if pitch_values else None,
                        "preceding_pause_seconds": max(0.0, start - previous_end)})
        previous_end = end
    for dimension in protocol["word_prominence"]["dimensions"]:
        available = [(index, row[dimension]) for index, row in enumerate(metrics) if row[dimension] is not None]
        scores = standardize([float(value) for _, value in available])
        for (index, _), score in zip(available, scores):
            metrics[index].setdefault("components", {})[dimension] = score
    for row in metrics:
        row["prominence"] = mean(row.get("components", {}).values()) if row.get("components") else 0.0
    return metrics


def flatten(features: dict[str, Any]) -> list[float]:
    values = []
    for value in features.values():
        values.extend(value if isinstance(value, list) else [value])
    return [float(value) for value in values]


def cluster_test(vectors: list[list[float]], labels: list[bool]) -> dict[str, Any]:
    matrix = np.asarray(vectors, dtype=float)
    matrix = (matrix - matrix.mean(axis=0)) / np.where(matrix.std(axis=0) > 1e-12, matrix.std(axis=0), 1)
    distances = np.sqrt(((matrix[:, None, :] - matrix[None, :, :]) ** 2).sum(axis=2))
    def statistic(candidate: list[bool]) -> float:
        within, between = [], []
        for i, j in combinations(range(len(candidate)), 2):
            (within if candidate[i] == candidate[j] else between).append(float(distances[i, j]))
        return mean(between) - mean(within)
    observed = statistic(labels)
    positives = sum(labels)
    null = []
    for selected in combinations(range(len(labels)), positives):
        selected_set = set(selected)
        null.append(statistic([index in selected_set for index in range(len(labels))]))
    p_value = sum(value >= observed - 1e-12 for value in null) / len(null)
    return {"statistic": observed, "exact_p_value": p_value, "permutations": len(null),
            "directional_success": observed > 0 and p_value <= 0.10}


def normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def execute(session_dir: Path, protocol_path: Path, alignments_path: Path, output: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text())
    bundle = json.loads((session_dir / "annotation-bundle.json").read_text())
    labels = json.loads((session_dir / "result.json").read_text())
    alignments = json.loads(alignments_path.read_text())
    bundle_items = {row["item_id"]: row for row in bundle["items"]}
    aligned = {row["item_id"]: row for row in alignments["items"]}
    label_items = {row["item_id"]: row for row in labels["items"]}
    if set(bundle_items) != set(aligned) or set(bundle_items) != set(label_items):
        raise ValueError("source item sets differ")
    items = []
    for item_id, item in bundle_items.items():
        path = session_dir / "assets" / item["file_name"]
        audio, rate = read_wav(path)
        fingerprint, _frames = clip_features(audio, rate, protocol)
        words = word_prominence(audio, rate, aligned[item_id]["words"], protocol)
        strongest = max(words, key=lambda row: row["prominence"])["word"]
        phrases = [normalize(part) for part in label_items[item_id]["annotation"]["perceived_focus"].split(",")]
        focus_hit = any(normalize(strongest) in phrase.split() for phrase in phrases)
        speech_acts = label_items[item_id]["annotation"]["speech_acts"]
        items.append({"item_id": item_id, "fingerprint": fingerprint, "words": words,
                      "strongest_word": strongest, "perceived_focus_hit": focus_hit,
                      "expressive": any(act != "neutral-statement" for act in speech_acts)})
    clustering = cluster_test([flatten(row["fingerprint"]) for row in items], [row["expressive"] for row in items])
    result = {"format": "conversation-prosody.acoustic-fingerprint-result", "version": 1,
              "summary": {"items": len(items), "focus_recovered": sum(row["perceived_focus_hit"] for row in items),
                          "expressive_items": sum(row["expressive"] for row in items), "clustering": clustering},
              "items": items}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--alignments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    args = parser.parse_args()
    result = execute(args.session_dir.resolve(), args.protocol.resolve(), args.alignments.resolve(), args.output.resolve())
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
