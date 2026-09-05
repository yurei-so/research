#!/usr/bin/env python3
"""Export inference ledger results and exact-match statistics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


FIELDS = ("focus_span", "focus_strength", "boundary", "delivery", "pace")


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    cases = {case["case_id"]: case for case in json.loads((run_dir / "corpus.json").read_text())}
    db = sqlite3.connect(run_dir / "ledger.sqlite3")
    rows: list[dict[str, Any]] = []
    for task_id, case_id, model, prompt_id, seed, response_json, semantic_error in db.execute(
        """SELECT task_id, case_id, model, prompt_id, seed, response_json, semantic_error
           FROM tasks WHERE status='complete' ORDER BY model, prompt_id, seed, case_id"""
    ):
        case = cases[case_id]
        predicted = json.loads(response_json)
        gold = case["gold_ir"]
        scores = {f"correct_{field}": int(predicted[field] == gold[field]) for field in FIELDS}
        rows.append({
            "task_id": task_id,
            "case_id": case_id,
            "pair_id": case["pair_id"],
            "phenomenon": case["phenomenon"],
            "model": model,
            "prompt_id": prompt_id,
            "seed": seed,
            "predicted_ir": predicted,
            "gold_ir": gold,
            "semantic_valid": int(semantic_error is None),
            "semantic_error": semantic_error,
            "exact_match": int(predicted == gold),
            **scores,
        })

    with (run_dir / "results.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["model"], row["prompt_id"])].append(row)
    summary_rows = []
    analysis: dict[str, Any] = {"task_groups": [], "pair_groups": []}
    for (model, prompt_id), items in sorted(groups.items()):
        summary = {"model": model, "prompt_id": prompt_id, "n": len(items)}
        for metric in ("semantic_valid", "exact_match", *(f"correct_{field}" for field in FIELDS)):
            successes = sum(item[metric] for item in items)
            summary[metric] = successes / len(items)
            analysis.setdefault("confidence_intervals", {}).setdefault(
                f"{model}|{prompt_id}", {}
            )[metric] = wilson(successes, len(items))
        summary_rows.append(summary)
        analysis["task_groups"].append(summary)

    pair_groups: dict[tuple[str, str], list[dict[str, int]]] = defaultdict(list)
    paired: dict[tuple[str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        paired[(row["model"], row["prompt_id"], row["seed"], row["pair_id"])].append(row)
    for (model, prompt_id, _seed, _pair_id), items in paired.items():
        if len(items) != 2:
            continue
        gold_differences = [field for field in FIELDS if items[0]["gold_ir"][field] != items[1]["gold_ir"][field]]
        prediction_differs = any(
            items[0]["predicted_ir"][field] != items[1]["predicted_ir"][field] for field in FIELDS
        )
        directional = all(
            item["predicted_ir"][field] == item["gold_ir"][field]
            for field in gold_differences
            for item in items
        )
        pair_groups[(model, prompt_id)].append({
            "both_exact": int(all(item["exact_match"] for item in items)),
            "prediction_differs": int(prediction_differs),
            "directional_contrast_correct": int(directional),
        })
    for (model, prompt_id), items in sorted(pair_groups.items()):
        summary: dict[str, Any] = {"model": model, "prompt_id": prompt_id, "n_pairs": len(items)}
        intervals = {}
        for metric in ("both_exact", "prediction_differs", "directional_contrast_correct"):
            successes = sum(item[metric] for item in items)
            summary[metric] = successes / len(items)
            intervals[metric] = wilson(successes, len(items))
        summary["confidence_intervals_95"] = intervals
        analysis["pair_groups"].append(summary)
    with (run_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_rows[0].keys() if summary_rows else ("model",))
        writer.writeheader()
        writer.writerows(summary_rows)
    (run_dir / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary_rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
