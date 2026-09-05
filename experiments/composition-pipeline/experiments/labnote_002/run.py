from __future__ import annotations

import argparse
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
            "type": "array",
            "minItems": 2,
            "maxItems": 16,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["op"],
                "properties": {
                    "op": {"enum": ["append", "replace", "delete", "finalize"]},
                    "text": {"type": "string"},
                    "old": {"type": "string"},
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


def _revision_prompt(task: str, draft: str, style: str) -> str:
    guidance = (
        "Make the smallest concise set of useful changes."
        if style == "concise"
        else "Preserve every correct part of the draft and change only what the task requires."
    )
    return f"""Revise a preloaded virtual text buffer using JSON operations.
The buffer initially contains the exact draft below. Do not append a replacement
copy of the whole draft. {guidance} Perform at least one append, exact unique
replace, or exact unique delete before finalizing. Finalize exactly once and
last. Return one JSON object only with an operations array and no markdown.

Allowed operations:
- {{"op":"append","text":"text to add"}}
- {{"op":"replace","old":"exact unique text","new":"replacement"}}
- {{"op":"delete","text":"exact unique text"}}
- {{"op":"finalize"}}

Task:
{task}

Preloaded draft:
{draft}"""


def _metric_record(
    *, final_text: str | None, draft: str, generated: dict[str, Any],
    protocol_success: bool, revision_count: int | None,
) -> dict[str, int | float | bool | None]:
    return {
        "protocol_success": protocol_success,
        "revision_operation_count": revision_count,
        "visible_character_count": len(final_text) if final_text is not None else None,
        "generated_token_count": generated["eval_count"],
        "prompt_token_count": generated["prompt_eval_count"],
        "draft_similarity": round(SequenceMatcher(None, draft, final_text).ratio(), 6)
        if final_text is not None else None,
        "latency_seconds": generated["elapsed_seconds"],
    }


def execute_trial(
    trial: Trial, *, cases: dict[str, dict[str, str]], model: str, base_url: str,
) -> dict[str, Any]:
    arm = str(trial.parameters["arm"])
    case_id = str(trial.parameters["case_id"])
    style = str(trial.parameters["prompt_style"])
    case = cases[case_id]
    seed = 20260822 + trial.repetition
    if arm == "direct_rewrite":
        generated = generate(
            base_url=base_url, model=model,
            prompt=_direct_prompt(case["task"], case["draft"], style), seed=seed,
        )
        final_text = generated["text"].strip()
        if not final_text:
            raise ValueError("empty direct rewrite")
        return {
            "metrics": _metric_record(
                final_text=final_text, draft=case["draft"], generated=generated,
                protocol_success=True, revision_count=None,
            ),
            "arm": arm, "case_id": case_id, "prompt_style": style,
            "repetition": trial.repetition, "final_text": final_text, "error": None,
        }

    if arm != "schema_revision":
        raise ValueError("unsupported campaign arm")
    generated = generate(
        base_url=base_url, model=model,
        prompt=_revision_prompt(case["task"], case["draft"], style),
        output_format=EDIT_SCHEMA, seed=seed,
    )
    final_text: str | None = None
    revision_count: int | None = None
    error: str | None = None
    try:
        document = json.loads(generated["text"])
        final_text, _ = apply_edit_document(
            document, initial_buffer=case["draft"], minimum_revision_operations=1,
            maximum_operations=16,
        )
        revision_count = sum(
            operation.get("op") != "finalize" for operation in document["operations"]
        )
    except json.JSONDecodeError:
        error = "invalid_json"
    except EditProtocolError as failure:
        error = str(failure)
    return {
        "metrics": _metric_record(
            final_text=final_text, draft=case["draft"], generated=generated,
            protocol_success=final_text is not None, revision_count=revision_count,
        ),
        "arm": arm, "case_id": case_id, "prompt_style": style,
        "repetition": trial.repetition, "final_text": final_text, "error": error,
    }


def _load_private_records(state_directory: Path) -> dict[str, dict[str, Any]]:
    state = json.loads((state_directory / "checkpoint.json").read_text())
    return state["trials"]


def _write_review_bundle(
    *, state_directory: Path, campaign_digest: str,
    cases: dict[str, dict[str, str]], records: dict[str, dict[str, Any]], trials: tuple[Trial, ...],
) -> tuple[int, str]:
    grouped: dict[tuple[str, str, int], dict[str, str]] = {}
    for trial in trials:
        record = records.get(trial.id)
        if not record or record["status"] != "completed":
            continue
        private = record.get("private_result", {})
        final_text = private.get("final_text")
        if not isinstance(final_text, str) or not final_text:
            continue
        key = (str(trial.parameters["case_id"]), str(trial.parameters["prompt_style"]), trial.repetition)
        grouped.setdefault(key, {})[str(trial.parameters["arm"])] = final_text

    pairs = []
    reveal = []
    for (case_id, style, repetition), outputs in sorted(grouped.items()):
        if set(outputs) != {"direct_rewrite", "schema_revision"}:
            continue
        pair_id = hashlib.sha256(
            f"{campaign_digest}:{case_id}:{style}:{repetition}".encode()
        ).hexdigest()[:24]
        direct_first = int(pair_id[-1], 16) % 2 == 0
        label_to_arm = {
            "A": "direct_rewrite" if direct_first else "schema_revision",
            "B": "schema_revision" if direct_first else "direct_rewrite",
        }
        case = cases[case_id]
        pairs.append({
            "pair_id": pair_id, "case_id": case_id, "prompt_style": style,
            "repetition": repetition, "task": case["task"], "draft": case["draft"],
            "candidate_a": outputs[label_to_arm["A"]],
            "candidate_b": outputs[label_to_arm["B"]],
            "criteria": ["instruction_adherence", "correctness", "concision", "voice_preservation", "unintended_changes"],
        })
        reveal.append({"pair_id": pair_id, "candidate_a_arm": label_to_arm["A"], "candidate_b_arm": label_to_arm["B"]})

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
    return len(pairs), bundle_digest


def run_labnote(*, state_directory: Path, model: str, base_url: str) -> dict[str, Any]:
    corpus = json.loads((ROOT / "corpus.json").read_text())
    cases = {case["id"]: case for case in corpus["cases"]}
    spec = load_campaign(ROOT / "manifest.json")
    campaign = run_campaign(
        spec, state_directory,
        lambda trial: execute_trial(trial, cases=cases, model=model, base_url=base_url),
    )
    records = _load_private_records(state_directory)
    arm_summary: dict[str, dict[str, int | float]] = {}
    for arm in ("direct_rewrite", "schema_revision"):
        matching = [
            records[trial.id] for trial in spec.trials
            if trial.parameters["arm"] == arm and trial.id in records
            and records[trial.id]["status"] == "completed"
        ]
        successes = sum(record["metrics"].get("protocol_success") is True for record in matching)
        arm_summary[arm] = {
            "completed_trials": len(matching),
            "protocol_success_rate": round(successes / len(matching), 6) if matching else 0,
        }
    pair_count, bundle_digest = _write_review_bundle(
        state_directory=state_directory, campaign_digest=spec.digest,
        cases=cases, records=records, trials=spec.trials,
    )
    return {
        "format": "composition-pipeline.experiment-result", "version": 1,
        "experiment": "labnote_002", "model": model,
        "campaign": {
            key: campaign[key] for key in (
                "campaign_digest", "planned_trials", "completed_trials",
                "successful_trials", "failed_trials", "stopped_reason",
            )
        },
        "summary": arm_summary,
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
