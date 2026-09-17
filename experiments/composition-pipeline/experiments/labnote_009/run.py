#!/usr/bin/env python3
"""Run Labnote 009: readiness-gated bounded-span repair."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from statistics import mean
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json
from composition_pipeline.ollama import generate


ROOT = Path(__file__).resolve().parent
BASE_PATH = ROOT.parent / "labnote_008" / "run.py"
BASE_SPEC = importlib.util.spec_from_file_location("labnote_008_base", BASE_PATH)
BASE = importlib.util.module_from_spec(BASE_SPEC); assert BASE_SPEC.loader; BASE_SPEC.loader.exec_module(BASE)

ARMS = ("hole-only", "readiness-span", "full-revision")
MODEL = "qwen3:8b"
TEMPERATURE = 0
NUM_PREDICT = 1536
TIMEOUT_SECONDS = 300
MINIMUM_COMPLETE_TRIPLETS = 6
OPEN_PATTERN = re.compile(r"\[\[DEFER_1:([A-Z][A-Z0-9_]*)\]\]")
CLOSE = "[[/DEFER_1]]"
READY = "[[READY_1]]"
ANY_MARKER = re.compile(r"\[\[(?:/?DEFER_|READY_)[^\]]*\]\]")
MINIMUM_RIGHT_CONTEXT_CHARACTERS = 24
MAXIMUM_REPLACEMENT_CHARACTERS = 1000

READINESS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["draft_with_span", "span_type", "ready_when"],
    "properties": {
        "draft_with_span": {"type": "string"},
        "span_type": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
        "ready_when": {"type": "array", "minItems": 1, "maxItems": 3,
                       "items": {"type": "string"}},
    },
}
REPAIR_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["replacement"],
    "properties": {"replacement": {"type": "string"}},
}


def normalize(text: str) -> str:
    return BASE.normalize(text)


def case_seed(case_id: str) -> int:
    return 20260918 + int(hashlib.sha256(case_id.encode()).hexdigest()[:6], 16)


def readiness_prompt(case: dict[str, str]) -> str:
    return f"""Revise the draft to satisfy the task using one readiness-gated provisional
span. Enclose every locally provisional claim that may need later context between exactly
one [[DEFER_1:TYPE]] and [[/DEFER_1]] marker. Continue generating substantive right-hand
context. Emit exactly one [[READY_1]] marker immediately after the generated context first
satisfies your declared ready_when conditions, then finish any remaining text. Do not
leave an incorrect claim outside the marked span merely to correct it later.

Return JSON matching the supplied schema. span_type is TYPE without brackets. ready_when
contains one to three short descriptions of evidence that later generated text must
provide before the provisional span can be resolved. draft_with_span contains the full
marked draft. The markers are runtime protocol and not user-visible prose.

Task:
{case['task']}

Draft:
{case['draft']}"""


def validate_readiness(value: dict[str, Any]) -> tuple[str, str, list[str], str]:
    draft = normalize(str(value.get("draft_with_span", "")))
    span_type = str(value.get("span_type", ""))
    ready_when = value.get("ready_when")
    openings = list(OPEN_PATTERN.finditer(draft))
    if len(openings) != 1 or draft.count(CLOSE) != 1 or draft.count(READY) != 1:
        raise ValueError("readiness draft must contain one complete span and one ready marker")
    opening = openings[0]
    if opening.group(1) != span_type:
        raise ValueError("declared span type does not match opening marker")
    close_at = draft.index(CLOSE)
    ready_at = draft.index(READY)
    if not (opening.end() < close_at < ready_at):
        raise ValueError("readiness markers are out of order")
    provisional = draft[opening.end():close_at].strip()
    right_context = draft[close_at + len(CLOSE):ready_at].strip()
    if not provisional:
        raise ValueError("bounded provisional span is empty")
    if len(right_context) < MINIMUM_RIGHT_CONTEXT_CHARACTERS:
        raise ValueError("ready marker lacks meaningful preceding right context")
    if (not isinstance(ready_when, list) or not 1 <= len(ready_when) <= 3
            or any(not isinstance(item, str) or not item.strip() or len(item) > 240
                   for item in ready_when)):
        raise ValueError("ready_when is outside its bounds")
    span_token = draft[opening.start():close_at + len(CLOSE)]
    visible_through_ready = draft[:ready_at]
    return draft, span_token, [item.strip() for item in ready_when], visible_through_ready


def repair_prompt(case: dict[str, str], visible_through_ready: str,
                  span_token: str, ready_when: list[str]) -> str:
    return f"""Resolve one readiness-gated provisional span. The draft below stops at the
point where its runtime readiness marker was emitted. Replace the entire marked span
using the task, its prefix, and the newly available right-hand context. Return JSON
matching the supplied schema. replacement must contain only the final text that replaces
the complete marked span; do not repeat markers or rewrite text outside that span.

Task:
{case['task']}

Declared readiness conditions:
{json.dumps(ready_when)}

Visible draft through readiness:
{visible_through_ready}{READY}

Exact span being replaced:
{span_token}"""


def call(*, model: str, base_url: str, prompt: str, seed: int,
         output_format: dict[str, Any] | None = None) -> dict[str, Any]:
    return generate(base_url=base_url, model=model, prompt=prompt,
                    output_format=output_format, temperature=TEMPERATURE, seed=seed,
                    num_predict=NUM_PREDICT, timeout_seconds=TIMEOUT_SECONDS, think=False)


def execute_trial(trial: Trial, *, cases: dict[str, dict[str, str]], model: str,
                  base_url: str) -> dict[str, Any]:
    arm = str(trial.parameters["arm"]); case_id = str(trial.parameters["case_id"])
    if arm not in ARMS:
        raise ValueError("unsupported composition arm")
    case = cases[case_id]; seed = case_seed(case_id); calls: list[dict[str, Any]] = []
    telemetry: dict[str, Any] | None = None

    if arm == "full-revision":
        first = call(model=model, base_url=base_url, prompt=BASE.direct_prompt(case), seed=seed)
        calls.append(first); first_text = normalize(first["text"])
        second = call(model=model, base_url=base_url,
                      prompt=BASE.revision_prompt(case, first_text), seed=seed)
        calls.append(second); final_text = normalize(second["text"])
    elif arm == "hole-only":
        first = call(model=model, base_url=base_url, prompt=BASE.deferred_prompt(case),
                     seed=seed, output_format=BASE.DEFERRED_SCHEMA)
        calls.append(first)
        draft, token, reason = BASE.validate_deferred(BASE.parse_json_object(first["text"]))
        hole_type = BASE.HOLE_PATTERN.search(token).group(1)
        second = call(model=model, base_url=base_url,
                      prompt=BASE.infill_prompt(case, draft, token, hole_type), seed=seed,
                      output_format=BASE.INFILL_SCHEMA)
        calls.append(second)
        replacement = BASE.validate_replacement(BASE.parse_json_object(second["text"]))
        final_text = normalize(draft.replace(token, replacement, 1))
        telemetry = {"mechanism": "hole-only", "type": hole_type, "reason": reason}
    else:
        first = call(model=model, base_url=base_url, prompt=readiness_prompt(case), seed=seed,
                     output_format=READINESS_SCHEMA)
        calls.append(first)
        draft, span_token, ready_when, visible = validate_readiness(
            BASE.parse_json_object(first["text"]))
        second = call(model=model, base_url=base_url,
                      prompt=repair_prompt(case, visible, span_token, ready_when), seed=seed,
                      output_format=REPAIR_SCHEMA)
        calls.append(second)
        replacement = BASE.validate_replacement(BASE.parse_json_object(second["text"]))
        final_text = normalize(draft.replace(span_token, replacement, 1).replace(READY, "", 1))
        telemetry = {"mechanism": "readiness-span", "ready_when": ready_when,
                     "visible_right_context_characters": len(visible.split(CLOSE, 1)[-1])}

    if not final_text or len(final_text) > 16_000 or ANY_MARKER.search(final_text):
        raise ValueError("final composition is invalid or contains protocol markers")
    return {
        "metrics": {"protocol_success": True, "call_count": len(calls),
                    "latency_seconds": round(sum(float(row["elapsed_seconds"]) for row in calls), 6),
                    "generated_token_count": sum(int(row.get("eval_count") or 0) for row in calls),
                    "prompt_token_count": sum(int(row.get("prompt_eval_count") or 0) for row in calls),
                    "final_character_count": len(final_text)},
        "arm": arm, "case_id": case_id, "seed": seed, "final_text": final_text,
        "protocol_telemetry": telemetry,
    }


def load_records(state_directory: Path) -> dict[str, dict[str, Any]]:
    return json.loads((state_directory / "checkpoint.json").read_text())["trials"]


def write_review(*, state_directory: Path, campaign_digest: str,
                 cases: dict[str, dict[str, str]], records: dict[str, dict[str, Any]],
                 trials: tuple[Trial, ...]) -> dict[str, Any]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for trial in trials:
        record = records.get(trial.id)
        if record and record["status"] == "completed":
            value = record["private_result"]
            grouped[str(trial.parameters["case_id"])][str(trial.parameters["arm"])] = value["final_text"]
    complete = {case_id: values for case_id, values in grouped.items() if set(values) == set(ARMS)}
    gate_passed = len(complete) >= MINIMUM_COMPLETE_TRIPLETS
    specs = {"hole-only-vs-readiness-span": ("hole-only", "readiness-span"),
             "full-revision-vs-readiness-span": ("full-revision", "readiness-span")}
    sessions = {}; automatic_ties = 0
    for name, (baseline, treatment) in specs.items():
        pairs = []; reveal = []
        if gate_passed:
            for case_id, outputs in sorted(complete.items()):
                if normalize(outputs[baseline]) == normalize(outputs[treatment]):
                    automatic_ties += 1; continue
                pair_id = hashlib.sha256(f"{campaign_digest}:{case_id}:{name}".encode()).hexdigest()[:24]
                baseline_first = int(pair_id[-1], 16) % 2 == 0
                labels = {"A": baseline if baseline_first else treatment,
                          "B": treatment if baseline_first else baseline}
                pairs.append({"pair_id": pair_id, "case_id": case_id,
                              "prompt_style": "readiness_span", "repetition": 0,
                              "task": cases[case_id]["task"], "draft": cases[case_id]["draft"],
                              "candidate_a": outputs[labels["A"]], "candidate_b": outputs[labels["B"]],
                              "criteria": ["instruction fidelity", "clarity", "concision", "naturalness"]})
                reveal.append({"pair_id": pair_id,
                               "candidate_a_arm": labels["A"].replace("-", "_"),
                               "candidate_b_arm": labels["B"].replace("-", "_")})
        bundle = {"format": "composition-pipeline.blinded-review", "version": 3,
                  "campaign_digest": campaign_digest, "pairs": pairs}
        digest = hashlib.sha256(json.dumps(bundle, sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
        key = {"format": "composition-pipeline.blinded-review-key", "version": 3,
               "campaign_digest": campaign_digest, "review_bundle_digest": digest,
               "baseline_arm": baseline.replace("-", "_"),
               "treatment_arm": treatment.replace("-", "_"), "pairs": reveal}
        write_private_json(state_directory / f"review-{name}-bundle.json", bundle)
        write_private_json(state_directory / f"review-{name}-key.json", key)
        sessions[name] = {"pair_count": len(pairs), "bundle_digest": digest,
                          "baseline_arm": baseline, "treatment_arm": treatment}
    intake = {"format": "composition-pipeline.readiness-review-intake", "version": 1,
              "complete_case_triplets": len(complete),
              "minimum_complete_case_triplets": MINIMUM_COMPLETE_TRIPLETS,
              "gate_passed": gate_passed, "automatic_tie_count": automatic_ties,
              "human_review_pair_count": sum(row["pair_count"] for row in sessions.values()),
              "sessions": sessions}
    write_private_json(state_directory / "review-intake-telemetry.json", intake)
    return intake


def arm_summary(records: dict[str, dict[str, Any]], arm: str) -> dict[str, int | float]:
    rows = [r["metrics"] for r in records.values() if r["status"] == "completed"
            and r["private_result"].get("arm") == arm]
    return {"completed_trials": len(rows),
            "mean_latency_seconds": round(mean(r["latency_seconds"] for r in rows), 6) if rows else 0,
            "mean_generated_tokens": round(mean(r["generated_token_count"] for r in rows), 3) if rows else 0,
            "mean_final_characters": round(mean(r["final_character_count"] for r in rows), 3) if rows else 0}


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text()); cases = {c["id"]: c for c in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(spec, state_directory,
                            lambda trial: execute_trial(trial, cases=cases, model=model, base_url=base_url))
    records = load_records(state_directory)
    review = write_review(state_directory=state_directory, campaign_digest=spec.digest,
                          cases=cases, records=records, trials=spec.trials)
    return {"format": "composition-pipeline.experiment-result", "version": 1,
            "experiment": "labnote_009", "model": model, "temperature": TEMPERATURE,
            "campaign": {k: campaign[k] for k in ("campaign_digest", "planned_trials",
                "completed_trials", "successful_trials", "failed_trials", "stopped_reason")},
            "summary": {arm: arm_summary(records, arm) for arm in ARMS}, "review": review}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--model", default=MODEL); parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args(); print(json.dumps(run_labnote(state_directory=args.state_dir,
        model=args.model, base_url=args.ollama_url), sort_keys=True))


if __name__ == "__main__": main()
