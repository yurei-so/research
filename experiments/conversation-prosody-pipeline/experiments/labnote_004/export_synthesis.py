#!/usr/bin/env python3
"""Export synthesis metadata and paired acoustic diagnostics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


def summarize(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"n": 0, "mean": 0.0, "median": 0.0, "sample_sd": 0.0}
    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / max(1, len(values) - 1)
    return {
        "n": len(values),
        "mean": average,
        "median": median(values),
        "sample_sd": math.sqrt(variance),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    cases = {case["case_id"]: case for case in json.loads((run_dir / "corpus.json").read_text())}
    db = sqlite3.connect(run_dir / "ledger.sqlite3")
    rows: list[dict[str, Any]] = []
    for values in db.execute(
        """SELECT task_id,case_id,condition,voice,audio_path,audio_sha256,
                  duration_seconds,rms,compiler_json
           FROM tasks WHERE status='complete' ORDER BY voice,condition,case_id"""
    ):
        task_id, case_id, condition, voice, path, digest, duration, rms, compiler = values
        case = cases[case_id]
        rows.append({
            "task_id": task_id,
            "case_id": case_id,
            "pair_id": case["pair_id"],
            "phenomenon": case["phenomenon"],
            "condition": condition,
            "voice": voice,
            "audio_path": path,
            "audio_sha256": digest,
            "duration_seconds": duration,
            "rms": rms,
            "compiler": json.loads(compiler),
        })
    with (run_dir / "results.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["voice"], row["condition"])].append(row)
    summaries = []
    for (voice, condition), items in sorted(groups.items()):
        summaries.append({
            "voice": voice,
            "condition": condition,
            **{f"duration_{key}": value for key, value in summarize([item["duration_seconds"] for item in items]).items()},
            **{f"rms_{key}": value for key, value in summarize([item["rms"] for item in items]).items()},
        })
    with (run_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summaries[0].keys() if summaries else ("voice",))
        writer.writeheader()
        writer.writerows(summaries)

    by_key = {(row["case_id"], row["voice"], row["condition"]): row for row in rows}
    paired = []
    for case_id in cases:
        for voice in sorted({row["voice"] for row in rows}):
            neutral = by_key.get((case_id, voice, "neutral"))
            gold = by_key.get((case_id, voice, "gold"))
            swapped = by_key.get((case_id, voice, "swapped"))
            if not (neutral and gold and swapped):
                continue
            paired.append({
                "case_id": case_id,
                "voice": voice,
                "phenomenon": cases[case_id]["phenomenon"],
                "gold_minus_neutral_duration": gold["duration_seconds"] - neutral["duration_seconds"],
                "swapped_minus_neutral_duration": swapped["duration_seconds"] - neutral["duration_seconds"],
                "gold_minus_neutral_rms": gold["rms"] - neutral["rms"],
                "swapped_minus_neutral_rms": swapped["rms"] - neutral["rms"],
            })
    with (run_dir / "paired-acoustic-diagnostics.jsonl").open("w") as handle:
        for row in paired:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"groups": summaries, "paired_rows": len(paired)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
