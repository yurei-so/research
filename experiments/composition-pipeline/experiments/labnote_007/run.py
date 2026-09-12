#!/usr/bin/env python3
"""Run Labnote 007: matched thinking-disabled versus thinking-enabled rewrites."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json
from composition_pipeline.ollama import generate


ROOT = Path(__file__).resolve().parent
ARMS = ("thinking-disabled", "thinking-enabled")
REVIEW_ARM = {"thinking-disabled": "direct_rewrite", "thinking-enabled": "thinking_enabled"}
MINIMUM_CHANGED_PAIRS = 8
MODEL = "qwen3:8b"
TEMPERATURE = 0
NUM_PREDICT = 4096
TIMEOUT_SECONDS = 600


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r", "").split("\n")).strip()


def prompt(case: dict[str, str]) -> str:
    return f"""Revise the draft to satisfy the task. Preserve correct wording and structure
unless a change is needed. Return only the revised text with no preface, analysis,
markdown fence, or commentary.

Task:
{case['task']}

Draft:
{case['draft']}"""


def case_seed(case_id: str) -> int:
    return 20260912 + int(hashlib.sha256(case_id.encode()).hexdigest()[:6], 16)


def execute_trial(trial: Trial, *, cases: dict[str, dict[str, str]], model: str,
                  base_url: str) -> dict[str, Any]:
    arm = str(trial.parameters["arm"])
    case_id = str(trial.parameters["case_id"])
    if arm not in ARMS:
        raise ValueError("unsupported reasoning arm")
    case = cases[case_id]
    result = generate(
        base_url=base_url, model=model, prompt=prompt(case), temperature=TEMPERATURE,
        seed=case_seed(case_id), num_predict=NUM_PREDICT,
        timeout_seconds=TIMEOUT_SECONDS, think=arm == "thinking-enabled",
    )
    final_text = normalize(result["text"])
    thinking = result.get("thinking", "")
    if not final_text or len(final_text) > 16_000:
        raise ValueError("final composition is outside its bounds")
    if arm == "thinking-enabled" and not thinking.strip():
        raise ValueError("thinking-enabled response omitted its thinking trace")
    if arm == "thinking-disabled" and thinking.strip():
        raise ValueError("thinking-disabled response unexpectedly returned a thinking trace")
    return {
        "metrics": {
            "protocol_success": True,
            "latency_seconds": float(result["elapsed_seconds"]),
            "generated_token_count": int(result.get("eval_count") or 0),
            "prompt_token_count": int(result.get("prompt_eval_count") or 0),
            "thinking_character_count": len(thinking),
            "final_character_count": len(final_text),
        },
        "arm": arm, "case_id": case_id, "seed": case_seed(case_id),
        "prompt": prompt(case), "final_text": final_text,
        "thinking": thinking, "thinking_sha256": hashlib.sha256(thinking.encode()).hexdigest(),
    }


def load_records(state_directory: Path) -> dict[str, dict[str, Any]]:
    return json.loads((state_directory / "checkpoint.json").read_text())["trials"]


def write_review(*, state_directory: Path, campaign_digest: str,
                 cases: dict[str, dict[str, str]], records: dict[str, dict[str, Any]],
                 trials: tuple[Trial, ...]) -> dict[str, Any]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for trial in trials:
        record = records.get(trial.id)
        if not record or record["status"] != "completed":
            continue
        private = record["private_result"]
        grouped[str(trial.parameters["case_id"])][str(trial.parameters["arm"])] = private["final_text"]

    changed: list[tuple[str, dict[str, str]]] = []
    automatic_ties = 0
    for case_id, outputs in sorted(grouped.items()):
        if set(outputs) != set(ARMS):
            continue
        if normalize(outputs[ARMS[0]]) == normalize(outputs[ARMS[1]]):
            automatic_ties += 1
        else:
            changed.append((case_id, outputs))
    gate_passed = len(changed) >= MINIMUM_CHANGED_PAIRS
    pairs: list[dict[str, Any]] = []
    reveal: list[dict[str, str]] = []
    if gate_passed:
        for case_id, outputs in changed:
            pair_id = hashlib.sha256(f"{campaign_digest}:{case_id}".encode()).hexdigest()[:24]
            disabled_first = int(pair_id[-1], 16) % 2 == 0
            labels = {"A": ARMS[0] if disabled_first else ARMS[1],
                      "B": ARMS[1] if disabled_first else ARMS[0]}
            pairs.append({
                "pair_id": pair_id, "case_id": case_id,
                "prompt_style": "preservation_first", "repetition": 0,
                "task": cases[case_id]["task"], "draft": cases[case_id]["draft"],
                "candidate_a": outputs[labels["A"]], "candidate_b": outputs[labels["B"]],
                "criteria": ["clarity", "fidelity", "concision", "naturalness"],
            })
            reveal.append({"pair_id": pair_id, "candidate_a_arm": REVIEW_ARM[labels["A"]],
                           "candidate_b_arm": REVIEW_ARM[labels["B"]]})
    bundle = {"format": "composition-pipeline.blinded-review", "version": 1,
              "campaign_digest": campaign_digest, "pairs": pairs}
    bundle_digest = hashlib.sha256(
        json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_private_json(state_directory / "review-bundle.json", bundle)
    write_private_json(state_directory / "review-key.json", {
        "format": "composition-pipeline.blinded-review-key", "version": 1,
        "campaign_digest": campaign_digest, "review_bundle_digest": bundle_digest,
        "pairs": reveal,
    })
    intake = {
        "format": "composition-pipeline.reasoning-review-intake", "version": 1,
        "matched_pair_count": sum(set(outputs) == set(ARMS) for outputs in grouped.values()),
        "automatic_tie_count": automatic_ties, "changed_pair_count": len(changed),
        "minimum_changed_pairs": MINIMUM_CHANGED_PAIRS, "gate_passed": gate_passed,
        "human_review_pair_count": len(pairs), "bundle_digest": bundle_digest,
    }
    write_private_json(state_directory / "review-intake-telemetry.json", intake)
    return intake


def arm_summary(records: dict[str, dict[str, Any]], arm: str) -> dict[str, int | float]:
    matching = [record for record in records.values()
                if record["status"] == "completed"
                and record["private_result"].get("arm") == arm]
    metrics = [record["metrics"] for record in matching]
    return {
        "completed_trials": len(matching),
        "mean_latency_seconds": round(mean(row["latency_seconds"] for row in metrics), 6) if metrics else 0,
        "mean_generated_tokens": round(mean(row["generated_token_count"] for row in metrics), 3) if metrics else 0,
        "mean_thinking_characters": round(mean(row["thinking_character_count"] for row in metrics), 3) if metrics else 0,
        "mean_final_characters": round(mean(row["final_character_count"] for row in metrics), 3) if metrics else 0,
    }


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(spec, state_directory,
                            lambda trial: execute_trial(trial, cases=cases, model=model, base_url=base_url))
    records = load_records(state_directory)
    review = write_review(state_directory=state_directory, campaign_digest=spec.digest,
                          cases=cases, records=records, trials=spec.trials)
    return {
        "format": "composition-pipeline.experiment-result", "version": 1,
        "experiment": "labnote_007", "model": model, "temperature": TEMPERATURE,
        "num_predict": NUM_PREDICT, "timeout_seconds": TIMEOUT_SECONDS,
        "campaign": {key: campaign[key] for key in (
            "campaign_digest", "planned_trials", "completed_trials", "successful_trials",
            "failed_trials", "stopped_reason")},
        "summary": {arm: arm_summary(records, arm) for arm in ARMS},
        "review": {key: review[key] for key in (
            "matched_pair_count", "automatic_tie_count", "changed_pair_count",
            "minimum_changed_pairs", "gate_passed", "human_review_pair_count", "bundle_digest")},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    print(json.dumps(run_labnote(state_directory=args.state_dir, model=args.model,
                                 base_url=args.ollama_url), sort_keys=True))


if __name__ == "__main__":
    main()
