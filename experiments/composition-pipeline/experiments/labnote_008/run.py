#!/usr/bin/env python3
"""Run Labnote 008: matched direct, full-revision, and deferred-infill composition."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from statistics import mean
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json
from composition_pipeline.ollama import generate


ROOT = Path(__file__).resolve().parent
ARMS = ("direct", "full-revision", "deferred-infill")
MODEL = "qwen3:8b"
TEMPERATURE = 0
NUM_PREDICT = 1536
TIMEOUT_SECONDS = 300
MINIMUM_COMPLETE_TRIPLETS = 6
HOLE_PATTERN = re.compile(r"\[\[DEFER_1:([A-Z][A-Z0-9_]*)\]\]")
ANY_HOLE_PATTERN = re.compile(r"\[\[DEFER_[^\]]*\]\]")
MINIMUM_RIGHT_CONTEXT_CHARACTERS = 24
MAXIMUM_REPLACEMENT_CHARACTERS = 600

DEFERRED_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["draft_with_hole", "hole_type", "reason"],
    "properties": {
        "draft_with_hole": {"type": "string"},
        "hole_type": {"type": "string", "pattern": "^[A-Z][A-Z0-9_]*$"},
        "reason": {"type": "string"},
    },
}
INFILL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["replacement"],
    "properties": {"replacement": {"type": "string"}},
}


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r", "").split("\n")).strip()


def case_seed(case_id: str) -> int:
    return 20260917 + int(hashlib.sha256(case_id.encode()).hexdigest()[:6], 16)


def direct_prompt(case: dict[str, str]) -> str:
    return f"""Revise the draft to satisfy the task. Preserve correct wording and structure
unless a change is needed. Return only the revised text with no preface, analysis,
markdown fence, or commentary.

Task:
{case['task']}

Draft:
{case['draft']}"""


def revision_prompt(case: dict[str, str], first_draft: str) -> str:
    return f"""Review the candidate against the task and return the best final version.
You may revise any part that improves instruction fidelity, clarity, concision, or
naturalness. Return only the final text with no preface, analysis, or markdown fence.

Task:
{case['task']}

Original draft:
{case['draft']}

Candidate:
{first_draft}"""


def deferred_prompt(case: dict[str, str]) -> str:
    return f"""Revise the draft to satisfy the task, but defer exactly one meaningful
phrase or clause whose best wording benefits from the later sentence context. At that
location emit exactly one typed token of the form [[DEFER_1:TYPE]], then continue and
finish the rest of the response. TYPE must be a short uppercase semantic category such
as CAUSE, QUALIFIER, CONTRAST, or DECISION_RULE. Include at least one substantive clause
after the token. Do not emit any other bracketed DEFER token.

Return JSON matching the supplied schema. draft_with_hole is the complete candidate with
the one token. hole_type is TYPE without brackets. reason briefly identifies the
material wording decision being deferred; it is experiment telemetry and will never be
shown as part of the final response.

Task:
{case['task']}

Draft:
{case['draft']}"""


def infill_prompt(case: dict[str, str], draft_with_hole: str, token: str,
                  hole_type: str) -> str:
    return f"""Fill exactly one deferred hole in a composition. Use both its left and
right context plus the task. Return JSON matching the supplied schema. replacement must
contain only the text that literally replaces {token}; it must not repeat the token,
rewrite surrounding text, add commentary, or introduce another placeholder.

Task:
{case['task']}

Hole type:
{hole_type}

Draft with hole:
{draft_with_hole}"""


def parse_json_object(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("structured response is not an object")
    return value


def validate_deferred(value: dict[str, Any]) -> tuple[str, str, str]:
    draft = normalize(str(value.get("draft_with_hole", "")))
    hole_type = str(value.get("hole_type", ""))
    reason = str(value.get("reason", "")).strip()
    matches = list(HOLE_PATTERN.finditer(draft))
    if len(matches) != 1 or len(ANY_HOLE_PATTERN.findall(draft)) != 1:
        raise ValueError("deferred draft must contain exactly one valid hole")
    if matches[0].group(1) != hole_type:
        raise ValueError("declared hole type does not match the token")
    if len(draft[matches[0].end():].strip()) < MINIMUM_RIGHT_CONTEXT_CHARACTERS:
        raise ValueError("deferred draft lacks meaningful right-hand context")
    if not reason or len(reason) > 600:
        raise ValueError("deferred reason is outside its bounds")
    return draft, matches[0].group(0), reason


def validate_replacement(value: dict[str, Any]) -> str:
    replacement = normalize(str(value.get("replacement", "")))
    if not replacement or len(replacement) > MAXIMUM_REPLACEMENT_CHARACTERS:
        raise ValueError("replacement is outside its bounds")
    if ANY_HOLE_PATTERN.search(replacement):
        raise ValueError("replacement contains a nested or unresolved hole")
    return replacement


def generate_once(*, model: str, base_url: str, prompt: str, seed: int,
                  output_format: dict[str, Any] | None = None) -> dict[str, Any]:
    return generate(base_url=base_url, model=model, prompt=prompt,
                    output_format=output_format, temperature=TEMPERATURE, seed=seed,
                    num_predict=NUM_PREDICT, timeout_seconds=TIMEOUT_SECONDS, think=False)


def execute_trial(trial: Trial, *, cases: dict[str, dict[str, str]], model: str,
                  base_url: str) -> dict[str, Any]:
    arm = str(trial.parameters["arm"])
    case_id = str(trial.parameters["case_id"])
    if arm not in ARMS:
        raise ValueError("unsupported composition arm")
    case = cases[case_id]
    seed = case_seed(case_id)
    calls: list[dict[str, Any]] = []
    deferred_telemetry: dict[str, Any] | None = None

    if arm in {"direct", "full-revision"}:
        first = generate_once(model=model, base_url=base_url,
                              prompt=direct_prompt(case), seed=seed)
        calls.append(first)
        first_text = normalize(first["text"])
        if arm == "direct":
            final_text = first_text
        else:
            second = generate_once(model=model, base_url=base_url,
                                   prompt=revision_prompt(case, first_text), seed=seed)
            calls.append(second)
            final_text = normalize(second["text"])
    else:
        first = generate_once(model=model, base_url=base_url,
                              prompt=deferred_prompt(case), seed=seed,
                              output_format=DEFERRED_SCHEMA)
        calls.append(first)
        structured = parse_json_object(first["text"])
        draft_with_hole, token, reason = validate_deferred(structured)
        hole_type = HOLE_PATTERN.search(token).group(1)  # validated above
        second = generate_once(model=model, base_url=base_url,
                               prompt=infill_prompt(case, draft_with_hole, token, hole_type),
                               seed=seed, output_format=INFILL_SCHEMA)
        calls.append(second)
        replacement = validate_replacement(parse_json_object(second["text"]))
        final_text = normalize(draft_with_hole.replace(token, replacement, 1))
        if ANY_HOLE_PATTERN.search(final_text):
            raise ValueError("final composition contains an unresolved hole")
        deferred_telemetry = {
            "hole_type": hole_type,
            "reason": reason,
            "token_offset": draft_with_hole.index(token),
            "right_context_character_count": len(draft_with_hole.split(token, 1)[1].strip()),
            "replacement_character_count": len(replacement),
        }

    if not final_text or len(final_text) > 16_000:
        raise ValueError("final composition is outside its bounds")
    return {
        "metrics": {
            "protocol_success": True,
            "call_count": len(calls),
            "latency_seconds": round(sum(float(call["elapsed_seconds"]) for call in calls), 6),
            "generated_token_count": sum(int(call.get("eval_count") or 0) for call in calls),
            "prompt_token_count": sum(int(call.get("prompt_eval_count") or 0) for call in calls),
            "final_character_count": len(final_text),
            "used_deferred_hole": deferred_telemetry is not None,
        },
        "arm": arm,
        "case_id": case_id,
        "seed": seed,
        "final_text": final_text,
        "deferred_telemetry": deferred_telemetry,
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
            private = record["private_result"]
            grouped[str(trial.parameters["case_id"])][str(trial.parameters["arm"])] = private["final_text"]

    complete = {case_id: outputs for case_id, outputs in grouped.items()
                if set(outputs) == set(ARMS)}
    gate_passed = len(complete) >= MINIMUM_COMPLETE_TRIPLETS
    automatic_ties = 0
    session_specs = {
        "direct-vs-deferred": ("direct", "deferred-infill"),
        "full-revision-vs-deferred": ("full-revision", "deferred-infill"),
    }
    sessions: dict[str, dict[str, Any]] = {}
    for session_name, (control, treatment) in session_specs.items():
        pairs: list[dict[str, Any]] = []
        reveal: list[dict[str, str]] = []
        if gate_passed:
            for case_id, outputs in sorted(complete.items()):
                if normalize(outputs[control]) == normalize(outputs[treatment]):
                    automatic_ties += 1
                    continue
                pair_id = hashlib.sha256(
                    f"{campaign_digest}:{case_id}:{session_name}".encode()).hexdigest()[:24]
                control_first = int(pair_id[-1], 16) % 2 == 0
                labels = {"A": control if control_first else treatment,
                          "B": treatment if control_first else control}
                pairs.append({
                    "pair_id": pair_id,
                    "case_id": case_id,
                    "prompt_style": "deferred_infill",
                    "repetition": 0,
                    "task": cases[case_id]["task"],
                    "draft": cases[case_id]["draft"],
                    "candidate_a": outputs[labels["A"]],
                    "candidate_b": outputs[labels["B"]],
                    "criteria": ["instruction fidelity", "clarity", "concision", "naturalness"],
                })
                reveal.append({"pair_id": pair_id, "candidate_a_arm": labels["A"],
                               "candidate_b_arm": labels["B"]})
        bundle = {"format": "composition-pipeline.blinded-review", "version": 3,
                  "campaign_digest": campaign_digest, "pairs": pairs}
        bundle_digest = hashlib.sha256(
            json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        write_private_json(state_directory / f"review-{session_name}-bundle.json", bundle)
        write_private_json(state_directory / f"review-{session_name}-key.json", {
            "format": "composition-pipeline.blinded-review-key", "version": 3,
            "campaign_digest": campaign_digest, "review_bundle_digest": bundle_digest,
            "baseline_arm": control.replace("-", "_"),
            "treatment_arm": treatment.replace("-", "_"),
            "pairs": [{**row,
                       "candidate_a_arm": row["candidate_a_arm"].replace("-", "_"),
                       "candidate_b_arm": row["candidate_b_arm"].replace("-", "_")}
                      for row in reveal],
        })
        sessions[session_name] = {"pair_count": len(pairs), "bundle_digest": bundle_digest,
                                  "baseline_arm": control, "treatment_arm": treatment}
    intake = {
        "format": "composition-pipeline.deferred-review-intake", "version": 1,
        "complete_case_triplets": len(complete),
        "minimum_complete_case_triplets": MINIMUM_COMPLETE_TRIPLETS,
        "gate_passed": gate_passed,
        "automatic_tie_count": automatic_ties,
        "human_review_pair_count": sum(session["pair_count"] for session in sessions.values()),
        "sessions": sessions,
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
        "mean_call_count": round(mean(row["call_count"] for row in metrics), 3) if metrics else 0,
        "mean_latency_seconds": round(mean(row["latency_seconds"] for row in metrics), 6) if metrics else 0,
        "mean_generated_tokens": round(mean(row["generated_token_count"] for row in metrics), 3) if metrics else 0,
        "mean_final_characters": round(mean(row["final_character_count"] for row in metrics), 3) if metrics else 0,
    }


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(spec, state_directory,
                            lambda trial: execute_trial(trial, cases=cases, model=model,
                                                        base_url=base_url))
    records = load_records(state_directory)
    review = write_review(state_directory=state_directory, campaign_digest=spec.digest,
                          cases=cases, records=records, trials=spec.trials)
    return {
        "format": "composition-pipeline.experiment-result", "version": 1,
        "experiment": "labnote_008", "model": model, "temperature": TEMPERATURE,
        "num_predict": NUM_PREDICT, "timeout_seconds": TIMEOUT_SECONDS,
        "campaign": {key: campaign[key] for key in (
            "campaign_digest", "planned_trials", "completed_trials", "successful_trials",
            "failed_trials", "stopped_reason")},
        "summary": {arm: arm_summary(records, arm) for arm in ARMS},
        "review": review,
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
