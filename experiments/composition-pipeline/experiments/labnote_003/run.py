from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign, write_private_json
from composition_pipeline.editor import EditProtocolError, apply_edit_document
from composition_pipeline.ollama import generate


ROOT = Path(__file__).resolve().parent
EDIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["operations"],
    "properties": {
        "operations": {
            "type": "array", "minItems": 1, "maxItems": 16,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["op"],
                "properties": {
                    "op": {"enum": ["append", "replace", "delete", "finalize"]},
                    "text": {"type": "string"}, "old": {"type": "string"},
                    "new": {"type": "string"},
                },
            },
        }
    },
}


def _direct_prompt(task: str, draft: str, style: str) -> str:
    guidance = (
        "Be concise and return only the revised text."
        if style == "concise"
        else "Preserve correct wording and structure unless a change is needed. Return only the revised text."
    )
    return f"Revise the draft to satisfy the task. {guidance}\n\nTask:\n{task}\n\nDraft:\n{draft}"


def _optional_editor_prompt(task: str, candidate: str, style: str) -> str:
    guidance = (
        "Prefer concision, but edit only when it materially improves the candidate."
        if style == "concise"
        else "Preserve correct wording and structure; edit only when a change is genuinely useful."
    )
    return f"""Inspect a candidate response in a bounded virtual text buffer.
The buffer initially contains the exact candidate below. {guidance}

You MAY finalize immediately without changing anything. Zero edits are valid and
preferred when the candidate already satisfies the task. Do not make an edit
merely to demonstrate tool use. If an edit is useful, use the smallest applicable
set of exact operations. Finalize exactly once and last. Return one JSON object
only with an operations array and no markdown.

Allowed operations:
- {{"op":"append","text":"text to add"}}
- {{"op":"replace","old":"exact unique text","new":"replacement"}}
- {{"op":"delete","text":"exact unique text"}}
- {{"op":"finalize"}}

Task:
{task}

Candidate buffer:
{candidate}"""


def _base_generation(
    case: dict[str, str], style: str, model: str, base_url: str, seed: int,
    temperature: float = 0,
) -> dict[str, Any]:
    return generate(
        base_url=base_url, model=model,
        prompt=_direct_prompt(case["task"], case["draft"], style), seed=seed,
        temperature=temperature,
    )


def _metric_record(
    *, final_text: str | None, source_draft: str, generations: list[dict[str, Any]],
    protocol_success: bool, editor_invoked: bool, revision_count: int | None,
) -> dict[str, Any]:
    return {
        "protocol_success": protocol_success,
        "editor_invoked": editor_invoked,
        "revision_operation_count": revision_count,
        "visible_character_count": len(final_text) if final_text is not None else None,
        "generated_token_count": sum(int(item.get("eval_count") or 0) for item in generations),
        "prompt_token_count": sum(int(item.get("prompt_eval_count") or 0) for item in generations),
        "draft_similarity": round(SequenceMatcher(None, source_draft, final_text).ratio(), 6)
        if final_text is not None else None,
        "latency_seconds": round(sum(float(item["elapsed_seconds"]) for item in generations), 6),
        "generation_count": len(generations),
    }


def execute_trial(
    trial: Trial, *, cases: dict[str, dict[str, str]], model: str, base_url: str,
    base_seed: int = 20260823, temperature: float = 0,
) -> dict[str, Any]:
    arm = str(trial.parameters["arm"])
    case_id = str(trial.parameters["case_id"])
    style = str(trial.parameters["prompt_style"])
    case = cases[case_id]
    seed = base_seed + trial.repetition
    base = _base_generation(case, style, model, base_url, seed, temperature)
    candidate = base["text"].strip()
    if not candidate:
        raise ValueError("empty direct rewrite")
    if arm == "direct_rewrite":
        return {
            "metrics": _metric_record(
                final_text=candidate, source_draft=case["draft"], generations=[base],
                protocol_success=True, editor_invoked=False, revision_count=None,
            ),
            "arm": arm, "case_id": case_id, "prompt_style": style,
            "repetition": trial.repetition, "final_text": candidate,
            "initial_candidate": candidate, "operations": None,
            "operation_types": None, "finalize_behavior": None, "error": None,
        }
    if arm != "optional_editor":
        raise ValueError("unsupported campaign arm")

    inspection = generate(
        base_url=base_url, model=model,
        prompt=_optional_editor_prompt(case["task"], candidate, style),
        output_format=EDIT_SCHEMA, seed=seed, temperature=temperature,
    )
    final_text: str | None = None
    operations: list[dict[str, Any]] | None = None
    operation_types: list[str] | None = None
    revision_count: int | None = None
    finalize_behavior: str | None = None
    error: str | None = None
    try:
        document = json.loads(inspection["text"])
        final_text, _ = apply_edit_document(
            document, initial_buffer=candidate, minimum_revision_operations=0,
            maximum_operations=16,
        )
        operations = document["operations"]
        operation_types = [str(operation["op"]) for operation in operations]
        revision_count = sum(kind != "finalize" for kind in operation_types)
        finalize_behavior = "unchanged" if revision_count == 0 else "edited"
    except json.JSONDecodeError:
        error = "invalid_json"
    except (EditProtocolError, KeyError, TypeError) as failure:
        error = str(failure)
    if final_text is None:
        final_text = candidate
        finalize_behavior = "fallback_unchanged"
    return {
        "metrics": _metric_record(
            final_text=final_text, source_draft=case["draft"], generations=[base, inspection],
            protocol_success=error is None, editor_invoked=True,
            revision_count=revision_count,
        ),
        "arm": arm, "case_id": case_id, "prompt_style": style,
        "repetition": trial.repetition, "final_text": final_text,
        "initial_candidate": candidate, "operations": operations,
        "operation_types": operation_types, "finalize_behavior": finalize_behavior,
        "error": error,
    }


def _load_private_records(state_directory: Path) -> dict[str, dict[str, Any]]:
    return json.loads((state_directory / "checkpoint.json").read_text())["trials"]


def _write_review_bundle(
    *, state_directory: Path, campaign_digest: str,
    cases: dict[str, dict[str, str]], records: dict[str, dict[str, Any]], trials: tuple[Trial, ...],
) -> tuple[int, str]:
    grouped: dict[tuple[str, str, int], dict[str, str]] = {}
    for trial in trials:
        record = records.get(trial.id)
        if not record or record["status"] != "completed":
            continue
        final_text = record.get("private_result", {}).get("final_text")
        if not isinstance(final_text, str) or not final_text:
            continue
        key = (str(trial.parameters["case_id"]), str(trial.parameters["prompt_style"]), trial.repetition)
        grouped.setdefault(key, {})[str(trial.parameters["arm"])] = final_text

    pairs, reveal = [], []
    for (case_id, style, repetition), outputs in sorted(grouped.items()):
        if set(outputs) != {"direct_rewrite", "optional_editor"}:
            continue
        pair_id = hashlib.sha256(
            f"{campaign_digest}:{case_id}:{style}:{repetition}".encode()
        ).hexdigest()[:24]
        direct_first = int(pair_id[-1], 16) % 2 == 0
        label_to_arm = {
            "A": "direct_rewrite" if direct_first else "optional_editor",
            "B": "optional_editor" if direct_first else "direct_rewrite",
        }
        case = cases[case_id]
        pairs.append({
            "pair_id": pair_id, "case_id": case_id, "prompt_style": style,
            "repetition": repetition, "task": case["task"], "draft": case["draft"],
            "candidate_a": outputs[label_to_arm["A"]],
            "candidate_b": outputs[label_to_arm["B"]],
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
    digest = hashlib.sha256(
        json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    write_private_json(state_directory / "review-bundle.json", bundle)
    write_private_json(state_directory / "review-key.json", {
        "format": "composition-pipeline.blinded-review-key", "version": 1,
        "campaign_digest": campaign_digest, "review_bundle_digest": digest,
        "pairs": reveal,
    })
    return len(pairs), digest


def _private_telemetry(records: dict[str, dict[str, Any]], trials: tuple[Trial, ...]) -> dict[str, Any]:
    treatment = [
        records[trial.id] for trial in trials
        if trial.parameters["arm"] == "optional_editor" and trial.id in records
        and records[trial.id]["status"] == "completed"
    ]
    valid = [record for record in treatment if record["metrics"].get("protocol_success") is True]
    fallback = [
        record for record in treatment
        if record["private_result"].get("finalize_behavior") == "fallback_unchanged"
    ]
    edited = [record for record in valid if record["private_result"].get("finalize_behavior") == "edited"]
    operation_types = Counter(
        kind for record in valid for kind in (record["private_result"].get("operation_types") or [])
        if kind != "finalize"
    )
    return {
        "format": "composition-pipeline.optional-editor-telemetry", "version": 1,
        "treatment_completed": len(treatment), "treatment_valid": len(valid),
        "finalized_unchanged": len(valid) - len(edited), "voluntarily_edited": len(edited),
        "transactional_fallback": len(fallback),
        "revision_operation_types": dict(sorted(operation_types.items())),
    }


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(
        spec, state_directory,
        lambda trial: execute_trial(trial, cases=cases, model=model, base_url=base_url),
    )
    records = _load_private_records(state_directory)
    summary: dict[str, dict[str, int | float]] = {}
    for arm in ("direct_rewrite", "optional_editor"):
        matching = [
            records[trial.id] for trial in spec.trials
            if trial.parameters["arm"] == arm and trial.id in records
            and records[trial.id]["status"] == "completed"
        ]
        successes = sum(record["metrics"].get("protocol_success") is True for record in matching)
        summary[arm] = {
            "completed_trials": len(matching),
            "protocol_success_rate": round(successes / len(matching), 6) if matching else 0,
        }
    write_private_json(
        state_directory / "treatment-telemetry.json",
        _private_telemetry(records, spec.trials),
    )
    pair_count, bundle_digest = _write_review_bundle(
        state_directory=state_directory, campaign_digest=spec.digest,
        cases=cases, records=records, trials=spec.trials,
    )
    return {
        "format": "composition-pipeline.experiment-result", "version": 1,
        "experiment": "labnote_003", "model": model,
        "campaign": {key: campaign[key] for key in (
            "campaign_digest", "planned_trials", "completed_trials",
            "successful_trials", "failed_trials", "stopped_reason",
        )},
        "summary": summary,
        "blinded_review": {"pair_count": pair_count, "bundle_digest": bundle_digest},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    print(json.dumps(run_labnote(
        state_directory=args.state_dir, model=args.model, base_url=args.ollama_url,
    ), separators=(",", ":")))


if __name__ == "__main__":
    main()
