#!/usr/bin/env python3
"""Run Labnote 006: targeted residual-defect diagnosis and repair."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json
from composition_pipeline.editor import EditProtocolError, apply_edit_document
from composition_pipeline.ollama import generate


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("labnote_003_base", ROOT.parent / "labnote_003" / "run.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("labnote_003 runner unavailable")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

DEFECTS = (
    "omission", "unsupported_addition", "instruction_violation",
    "awkward_structure", "tone_mismatch", "ambiguity", "redundancy", "none",
)
DIAGNOSIS_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["defect", "evidence", "repair_instruction"],
    "properties": {
        "defect": {"enum": list(DEFECTS)},
        "evidence": {"type": "string", "maxLength": 500},
        "repair_instruction": {"type": "string", "maxLength": 500},
    },
}
VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["defect_fixed", "material_regression"],
    "properties": {
        "defect_fixed": {"type": "boolean"},
        "material_regression": {"type": "boolean"},
    },
}
def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r", "").split("\n")).strip()


def _diagnosis_prompt(task: str, candidate: str) -> str:
    return f"""Audit the candidate against the task. Select only its single most important
residual defect from this frozen taxonomy: {', '.join(DEFECTS)}. Choose none if
there is no material defect. Evidence must quote an exact substring of the
candidate (or be empty for omission/none). Give one narrow repair instruction;
use an empty instruction for none. Return JSON only.

Task:\n{task}\n\nCandidate:\n{candidate}"""


def _repair_prompt(task: str, candidate: str, defect: str, instruction: str) -> str:
    return f"""Repair exactly one diagnosed defect in a bounded virtual text buffer.
Preserve everything not required by the repair. Return only the complete
repaired buffer with no JSON, markdown fence, preface, or commentary. The
controller will apply it as one exact whole-buffer replacement.

Task:\n{task}\n\nDefect: {defect}\nRepair instruction: {instruction}

Candidate buffer:\n{candidate}"""


def _verify_prompt(task: str, baseline: str, repaired: str, defect: str, instruction: str) -> str:
    return f"""Independently compare a baseline and targeted repair. Report whether the
named defect was actually fixed and whether the repair introduced any material
regression in instruction following, factual fidelity, clarity, concision, or
naturalness. Return JSON only.

Task:\n{task}\n\nNamed defect: {defect}\n+Repair instruction: {instruction}\n\nBaseline:\n{baseline}\n\nRepaired:\n{repaired}"""


def execute_trial(trial: Trial, *, cases: dict[str, dict[str, str]], model: str, base_url: str) -> dict[str, Any]:
    case_id = str(trial.parameters["case_id"])
    style = str(trial.parameters["prompt_style"])
    case = cases[case_id]
    seed = 20260826 + trial.repetition
    temperature = float(trial.parameters["sampling_temperature"])
    generations: list[dict[str, Any]] = []
    base = BASE._base_generation(case, style, model, base_url, seed, temperature)
    generations.append(base)
    baseline = base["text"].strip()
    if not baseline:
        raise ValueError("empty direct rewrite")

    diagnosis_call = generate(base_url=base_url, model=model,
        prompt=_diagnosis_prompt(case["task"], baseline), output_format=DIAGNOSIS_SCHEMA,
        seed=seed + 10_000, temperature=0)
    generations.append(diagnosis_call)
    diagnosis = json.loads(diagnosis_call["text"])
    defect = diagnosis["defect"]
    evidence = diagnosis["evidence"]
    instruction = diagnosis["repair_instruction"]
    if defect not in DEFECTS or not isinstance(evidence, str) or not isinstance(instruction, str):
        raise ValueError("invalid diagnosis")
    if evidence and evidence not in baseline:
        raise ValueError("diagnostic evidence is not an exact candidate substring")
    if defect == "none":
        return _result(case_id, style, trial.repetition, baseline, baseline, defect,
            evidence, instruction, False, False, generations, None)
    if not instruction.strip():
        raise ValueError("diagnosed defect requires a repair instruction")

    repair_call = generate(base_url=base_url, model=model,
        prompt=_repair_prompt(case["task"], baseline, defect, instruction),
        seed=seed + 20_000, temperature=0)
    generations.append(repair_call)
    try:
        replacement = repair_call["text"].strip()
        if not replacement or len(replacement) > 16_000:
            raise ValueError("replacement buffer is outside its bounds")
        document = {"operations": [
            {"op": "replace", "old": baseline, "new": replacement},
            {"op": "finalize"},
        ]}
        repaired, _ = apply_edit_document(document, initial_buffer=baseline,
            minimum_revision_operations=1, maximum_operations=16)
    except (json.JSONDecodeError, EditProtocolError, KeyError, TypeError) as error:
        return _result(case_id, style, trial.repetition, baseline, baseline, defect,
            evidence, instruction, False, False, generations, str(error))

    verify_call = generate(base_url=base_url, model=model,
        prompt=_verify_prompt(case["task"], baseline, repaired, defect, instruction),
        output_format=VERIFY_SCHEMA, seed=seed + 30_000, temperature=0)
    generations.append(verify_call)
    verification = json.loads(verify_call["text"])
    verified = verification.get("defect_fixed") is True and verification.get("material_regression") is False
    return _result(case_id, style, trial.repetition, baseline, repaired, defect,
        evidence, instruction, True, verified, generations, None)


def _result(case_id: str, style: str, repetition: int, baseline: str, repaired: str,
            defect: str, evidence: str, instruction: str, repair_attempted: bool,
            verified: bool, generations: list[dict[str, Any]], error: str | None) -> dict[str, Any]:
    changed = normalize(baseline) != normalize(repaired)
    return {
        "metrics": {
            "protocol_success": error is None, "defect_detected": defect != "none",
            "repair_attempted": repair_attempted, "changed": changed,
            "verified_repair": verified and changed,
            "generation_count": len(generations),
            "generated_token_count": sum(int(item.get("eval_count") or 0) for item in generations),
            "prompt_token_count": sum(int(item.get("prompt_eval_count") or 0) for item in generations),
            "latency_seconds": round(sum(float(item["elapsed_seconds"]) for item in generations), 6),
        },
        "case_id": case_id, "prompt_style": style, "repetition": repetition,
        "baseline": baseline, "repaired": repaired, "defect": defect,
        "evidence": evidence, "repair_instruction": instruction, "error": error,
    }


def _pair_digest(baseline: str, repaired: str) -> str:
    ordered = sorted((normalize(baseline), normalize(repaired)))
    return hashlib.sha256(f"{ordered[0]}\0{ordered[1]}".encode()).hexdigest()


def write_review_intake(*, state_directory: Path, campaign_digest: str,
                        cases: dict[str, dict[str, str]], records: dict[str, Any],
                        trials: tuple[Trial, ...]) -> dict[str, Any]:
    groups: dict[str, list[tuple[Trial, dict[str, Any]]]] = {}
    for trial in trials:
        record = records.get(trial.id)
        if not record or record["status"] != "completed" or record["metrics"].get("verified_repair") is not True:
            continue
        private = record["private_result"]
        groups.setdefault(_pair_digest(private["baseline"], private["repaired"]), []).append((trial, private))
    eligible_cases = {str(items[0][0].parameters["case_id"]) for items in groups.values()}
    gate_passed = len(groups) >= 12 and len(eligible_cases) >= 6
    pairs, reveal = [], []
    if gate_passed:
        for digest, items in sorted(groups.items()):
            trial, private = items[0]
            pair_id = hashlib.sha256(f"{campaign_digest}:{digest}".encode()).hexdigest()[:24]
            baseline_first = int(pair_id[-1], 16) % 2 == 0
            pairs.append({
                "pair_id": pair_id, "case_id": private["case_id"],
                "task": cases[private["case_id"]]["task"],
                "candidate_a": private["baseline"] if baseline_first else private["repaired"],
                "candidate_b": private["repaired"] if baseline_first else private["baseline"],
                "criteria": ["instruction_following", "fidelity", "clarity", "concision", "naturalness"],
            })
            reveal.append({"pair_id": pair_id, "candidate_a_arm": "baseline" if baseline_first else "targeted_repair",
                           "candidate_b_arm": "targeted_repair" if baseline_first else "baseline"})
    bundle = {"format": "composition-pipeline.blinded-review", "version": 1,
              "campaign_digest": campaign_digest, "pairs": pairs}
    bundle_digest = hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_private_json(state_directory / "review-bundle.json", bundle)
    write_private_json(state_directory / "review-key.json", {
        "format": "composition-pipeline.blinded-review-key", "version": 1,
        "campaign_digest": campaign_digest, "review_bundle_digest": bundle_digest, "pairs": reveal,
    })
    sizes = sorted((len(items) for items in groups.values()), reverse=True)
    intake = {"format": "composition-pipeline.review-intake-telemetry", "version": 1,
              "verified_changed_trials": sum(sizes), "unique_verified_pairs": len(groups),
              "duplicate_verified_trials": sum(size - 1 for size in sizes),
              "eligible_case_count": len(eligible_cases), "gate_passed": gate_passed,
              "human_review_pair_count": len(pairs), "bundle_digest": bundle_digest,
              "multiplicity_counts": dict(sorted(Counter(sizes).items()))}
    write_private_json(state_directory / "review-intake-telemetry.json", intake)
    return intake


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(spec, state_directory,
        lambda trial: execute_trial(trial, cases=cases, model=model, base_url=base_url))
    records = BASE._load_private_records(state_directory)
    intake = write_review_intake(state_directory=state_directory, campaign_digest=spec.digest,
        cases=cases, records=records, trials=spec.trials)
    defects = Counter(record["private_result"].get("defect") for record in records.values()
                      if record["status"] == "completed")
    write_private_json(state_directory / "defect-telemetry.json", {
        "format": "composition-pipeline.defect-telemetry", "version": 1,
        "defect_counts": dict(sorted(defects.items())),
    })
    return {"format": "composition-pipeline.experiment-result", "version": 1,
            "experiment": "labnote_006", "model": model,
            "campaign": {key: campaign[key] for key in ("campaign_digest", "planned_trials",
                "completed_trials", "successful_trials", "failed_trials", "stopped_reason")},
            "review": {key: intake[key] for key in ("verified_changed_trials", "unique_verified_pairs",
                "duplicate_verified_trials", "eligible_case_count", "gate_passed",
                "human_review_pair_count", "bundle_digest")}}


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
