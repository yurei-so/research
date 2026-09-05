#!/usr/bin/env python3
"""Analyze safe reuse and net latency for Labnote 005b response plans."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

REUSABLE = {"exact", "lightweight_repair"}


def endpoint_ok(prediction: dict, gold: dict) -> bool:
    return prediction["intent"] == gold["intent"] and prediction["topic"] == gold["topic"]


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * quantile)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction-dir", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    prediction_root, root = Path(args.prediction_dir), Path(args.run_dir)
    turns = json.loads((prediction_root / "corpus.json").read_text())
    turn_by_id = {turn["turn_id"]: turn for turn in turns}
    manifest = json.loads((root / "manifest.json").read_text())
    seeds = manifest["seeds"]
    db = sqlite3.connect(root / "ledger.sqlite3")
    final = {(turn_id, seed): (json.loads(plan), duration or 0)
             for turn_id, seed, plan, duration in db.execute(
                 "SELECT turn_id,seed,plan,duration_ns FROM final_plans WHERE status='complete'")}
    rows = list(db.execute("""SELECT condition,turn_id,seed,snapshot,head_start_ms,prediction,
      speculative_duration_ns,grade,validation_duration_ns,repair_duration_ns
      FROM branches WHERE status='complete'"""))
    by_key = {(condition, turn_id, seed): row for row in rows for condition, turn_id, seed in [row[:3]]}
    report = []
    details = []
    for condition in manifest["conditions"]:
        outcomes = []
        for turn in turns:
            for seed in seeds:
                baseline_ns = final[(turn["turn_id"], seed)][1]
                row = by_key.get((condition, turn["turn_id"], seed))
                if row is None:
                    outcome = {"condition": condition, "turn_id": turn["turn_id"], "seed": seed,
                               "archetype": turn["archetype"], "branch": False, "grade": "no_branch",
                               "reusable": False, "baseline_ms": baseline_ns / 1e6,
                               "committed_ms": baseline_ns / 1e6, "net_saved_ms": 0.0, "wasted_compute_ms": 0.0}
                else:
                    _, _, _, snapshot, head_start_ms, prediction_json, speculative_ns, grade, validation_ns, repair_ns = row
                    spec_ms, validation_ms, repair_ms = speculative_ns / 1e6, validation_ns / 1e6, repair_ns / 1e6
                    ready_after_end = max(0.0, spec_ms - head_start_ms)
                    prediction_valid = endpoint_ok(json.loads(prediction_json), turn["gold_endpoint"])
                    judge_accepted = grade in REUSABLE
                    reusable = prediction_valid and judge_accepted
                    if reusable:
                        committed_ms = ready_after_end + validation_ms + repair_ms
                    else:
                        # Verification must finish before a rejected branch falls back to
                        # generation from the locked final turn.
                        committed_ms = ready_after_end + validation_ms + baseline_ns / 1e6
                    outcome = {"condition": condition, "turn_id": turn["turn_id"], "seed": seed,
                               "archetype": turn["archetype"], "snapshot": snapshot, "branch": True,
                               "grade": grade, "prediction_valid": prediction_valid,
                               "judge_accepted": judge_accepted, "judge_accepted_invalid": judge_accepted and not prediction_valid,
                               "reusable": reusable, "head_start_ms": head_start_ms,
                               "speculative_ms": spec_ms, "validation_ms": validation_ms, "repair_ms": repair_ms,
                               "baseline_ms": baseline_ns / 1e6, "committed_ms": committed_ms,
                               "net_saved_ms": baseline_ns / 1e6 - committed_ms,
                               "wasted_compute_ms": 0.0 if reusable else spec_ms}
                outcomes.append(outcome); details.append(outcome)
        savings = [item["net_saved_ms"] for item in outcomes]
        branch_outcomes = [item for item in outcomes if item["branch"]]
        grades = Counter(item["grade"] for item in outcomes)
        by_archetype = defaultdict(list)
        for item in outcomes:
            by_archetype[item["archetype"]].append(item)
        report.append({
            "condition": condition, "n": len(outcomes), "branch_start_rate": len(branch_outcomes) / len(outcomes),
            "grade_rates": {grade: count / len(outcomes) for grade, count in sorted(grades.items())},
            "usable_speculative_work_rate": sum(item["reusable"] for item in outcomes) / len(outcomes),
            "mean_net_saved_ms": mean(savings), "median_net_saved_ms": median(savings),
            "p10_net_saved_ms": percentile(savings, .10), "p90_net_saved_ms": percentile(savings, .90),
            "positive_net_latency_rate": sum(value > 0 for value in savings) / len(savings),
            "mean_wasted_compute_ms": mean(item["wasted_compute_ms"] for item in outcomes),
            "judge_accepted_invalid_branch_rate": sum(item.get("judge_accepted_invalid", False) for item in outcomes) / len(outcomes),
            "late_reversal_early_promotion_rate": sum(item["reusable"] and item.get("snapshot", 3) < 3
                                                        for item in by_archetype["reversal"]) / len(by_archetype["reversal"]),
            "invalid_endpoint_promotion_rate": (
                sum(item["reusable"] for item in branch_outcomes if not item.get("prediction_valid", False)) /
                max(1, sum(not item.get("prediction_valid", False) for item in branch_outcomes))
            ),
            "archetypes": {name: {"usable_rate": sum(item["reusable"] for item in group) / len(group),
                                     "mean_net_saved_ms": mean(item["net_saved_ms"] for item in group)}
                           for name, group in sorted(by_archetype.items())},
        })
    (root / "downstream-details.json").write_text(json.dumps(details, indent=2, sort_keys=True) + "\n")
    (root / "downstream-analysis.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
