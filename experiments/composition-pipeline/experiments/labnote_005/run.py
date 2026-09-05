#!/usr/bin/env python3
"""Run Labnote 005: stochastic generation with deduplicated changed review pairs."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json


ROOT = Path(__file__).resolve().parent
PRIOR_ROOT = ROOT.parent / "labnote_004"
SPEC = importlib.util.spec_from_file_location("labnote_004_base", PRIOR_ROOT / "run.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("labnote_004 runner unavailable")
PRIOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PRIOR)
BASE = PRIOR.BASE


def pair_digest(baseline: str, final_text: str) -> str:
    ordered = sorted((PRIOR.normalize_output(baseline), PRIOR.normalize_output(final_text)))
    return hashlib.sha256(f"{ordered[0]}\0{ordered[1]}".encode()).hexdigest()


def write_unique_review_bundle(
    *, state_directory: Path, campaign_digest: str,
    cases: dict[str, dict[str, str]], records: dict[str, dict[str, Any]],
    trials: tuple[Trial, ...],
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = {}
    for trial in trials:
        record = records.get(trial.id)
        if not record or record["status"] != "completed":
            continue
        private_result = record.get("private_result", {})
        if not isinstance(private_result.get("final_text"), str):
            continue
        key = (str(trial.parameters["case_id"]), str(trial.parameters["prompt_style"]), trial.repetition)
        grouped.setdefault(key, {})[str(trial.parameters["arm"])] = private_result

    changed: dict[str, list[tuple[str, str, int, str, str]]] = {}
    matched_pairs = automatic_ties = 0
    for (case_id, style, repetition), records_by_arm in sorted(grouped.items()):
        if set(records_by_arm) != {"direct_rewrite", "optional_editor"}:
            continue
        treatment = records_by_arm["optional_editor"]
        baseline = treatment.get("initial_candidate")
        final_text = treatment.get("final_text")
        if not isinstance(baseline, str) or not baseline or not isinstance(final_text, str) or not final_text:
            continue
        matched_pairs += 1
        if PRIOR.normalize_output(baseline) == PRIOR.normalize_output(final_text):
            automatic_ties += 1
            continue
        changed.setdefault(pair_digest(baseline, final_text), []).append(
            (case_id, style, repetition, baseline, final_text)
        )

    pairs, reveal = [], []
    for digest, occurrences in sorted(changed.items()):
        case_id, style, repetition, baseline, final_text = occurrences[0]
        pair_id = hashlib.sha256(f"{campaign_digest}:{digest}".encode()).hexdigest()[:24]
        direct_first = int(pair_id[-1], 16) % 2 == 0
        label_to_arm = {
            "A": "direct_rewrite" if direct_first else "optional_editor",
            "B": "optional_editor" if direct_first else "direct_rewrite",
        }
        case = cases[case_id]
        pairs.append({
            "pair_id": pair_id, "case_id": case_id, "prompt_style": style,
            "repetition": repetition, "task": case["task"], "draft": case["draft"],
            "candidate_a": baseline if label_to_arm["A"] == "direct_rewrite" else final_text,
            "candidate_b": baseline if label_to_arm["B"] == "direct_rewrite" else final_text,
            "criteria": ["clarity", "fidelity", "concision", "naturalness"],
        })
        reveal.append({
            "pair_id": pair_id, "candidate_a_arm": label_to_arm["A"],
            "candidate_b_arm": label_to_arm["B"],
        })

    bundle = {
        "format": "composition-pipeline.blinded-review", "version": 1,
        "campaign_digest": campaign_digest, "pairs": pairs,
    }
    bundle_digest = hashlib.sha256(
        json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    write_private_json(state_directory / "review-bundle.json", bundle)
    write_private_json(state_directory / "review-key.json", {
        "format": "composition-pipeline.blinded-review-key", "version": 1,
        "campaign_digest": campaign_digest, "review_bundle_digest": bundle_digest,
        "pairs": reveal,
    })
    group_sizes = sorted((len(items) for items in changed.values()), reverse=True)
    intake = {
        "format": "composition-pipeline.review-intake-telemetry", "version": 1,
        "matched_pair_count": matched_pairs,
        "automatic_tie_count": automatic_ties,
        "changed_trial_count": sum(group_sizes),
        "unique_review_pair_count": len(changed),
        "duplicate_changed_trial_count": sum(size - 1 for size in group_sizes),
        "duplicate_group_size_counts": dict(sorted(Counter(group_sizes).items())),
    }
    write_private_json(state_directory / "review-intake-telemetry.json", intake)
    return {**intake, "bundle_digest": bundle_digest}


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT.parent / "labnote_003" / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(
        spec, state_directory,
        lambda trial: BASE.execute_trial(
            trial, cases=cases, model=model, base_url=base_url,
            base_seed=20260825, temperature=0.35,
        ),
    )
    records = BASE._load_private_records(state_directory)
    summary = {}
    for arm in ("direct_rewrite", "optional_editor"):
        matching = [records[trial.id] for trial in spec.trials
            if trial.parameters["arm"] == arm and trial.id in records
            and records[trial.id]["status"] == "completed"]
        successes = sum(record["metrics"].get("protocol_success") is True for record in matching)
        summary[arm] = {"completed_trials": len(matching),
            "protocol_success_rate": round(successes / len(matching), 6) if matching else 0}
    write_private_json(state_directory / "treatment-telemetry.json", BASE._private_telemetry(records, spec.trials))
    review = write_unique_review_bundle(
        state_directory=state_directory, campaign_digest=spec.digest,
        cases=cases, records=records, trials=spec.trials,
    )
    public_review = {key: review[key] for key in (
        "matched_pair_count", "automatic_tie_count", "changed_trial_count",
        "unique_review_pair_count", "duplicate_changed_trial_count",
        "duplicate_group_size_counts", "bundle_digest",
    )}
    return {
        "format": "composition-pipeline.experiment-result", "version": 1,
        "experiment": "labnote_005", "model": model, "temperature": 0.35,
        "campaign": {key: campaign[key] for key in (
            "campaign_digest", "planned_trials", "completed_trials",
            "successful_trials", "failed_trials", "stopped_reason")},
        "summary": summary, "review": public_review,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    print(json.dumps(run_labnote(state_directory=args.state_dir, model=args.model,
        base_url=args.ollama_url), sort_keys=True))


if __name__ == "__main__":
    main()
