from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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
            "minItems": 1,
            "maxItems": 64,
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


def edit_prompt(task: str) -> str:
    return f"""Complete the writing task using a virtual text buffer.
Return one JSON object only, with an operations array. Allowed operations:
- {{"op":"append","text":"text to add"}}
- {{"op":"replace","old":"exact unique text already in the buffer","new":"replacement"}}
- {{"op":"delete","text":"exact unique text already in the buffer"}}
- {{"op":"finalize"}}

Build a useful final response. Revise only when revision materially helps; edits
are optional. Finalize exactly once as the last operation. Do not explain the
protocol and do not include markdown fences.

Writing task: {task}"""


def run_edit_arm(*, task: str, model: str, base_url: str, constrained: bool) -> dict[str, Any]:
    generated = generate(
        base_url=base_url,
        model=model,
        prompt=edit_prompt(task),
        output_format=EDIT_SCHEMA if constrained else None,
    )
    record: dict[str, Any] = {
        "parse_success": False,
        "semantic_apply_success": False,
        "finalize_success": False,
        "edit_operation_count": None,
        "final_text": None,
        "visible_character_count": None,
        "generated_token_count": generated["eval_count"],
        "prompt_token_count": generated["prompt_eval_count"],
        "latency_seconds": generated["elapsed_seconds"],
        "error": None,
    }
    try:
        document = json.loads(generated["text"])
        record["parse_success"] = True
        final_text, edit_count = apply_edit_document(document)
        record.update({
            "semantic_apply_success": True,
            "finalize_success": True,
            "edit_operation_count": edit_count,
            "final_text": final_text,
            "visible_character_count": len(final_text),
        })
    except json.JSONDecodeError:
        record["error"] = "invalid_json"
    except EditProtocolError as error:
        record["error"] = str(error)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    corpus = json.loads((ROOT / "corpus.json").read_text())
    results = []
    for case in corpus["cases"]:
        append = generate(base_url=args.ollama_url, model=args.model, prompt=case["prompt"])
        results.append({
            "case_id": case["id"],
            "append_only": {
                "final_text": append["text"],
                "visible_character_count": len(append["text"]),
                "generated_token_count": append["eval_count"],
                "prompt_token_count": append["prompt_eval_count"],
                "latency_seconds": append["elapsed_seconds"],
            },
            "edit_unconstrained": run_edit_arm(
                task=case["prompt"], model=args.model, base_url=args.ollama_url, constrained=False,
            ),
            "edit_schema_constrained": run_edit_arm(
                task=case["prompt"], model=args.model, base_url=args.ollama_url, constrained=True,
            ),
        })

    summary = {}
    for arm in ("edit_unconstrained", "edit_schema_constrained"):
        records = [result[arm] for result in results]
        summary[arm] = {
            "parse_success_rate": sum(record["parse_success"] for record in records) / len(records),
            "semantic_apply_success_rate": sum(
                record["semantic_apply_success"] for record in records
            ) / len(records),
            "total_edits": sum(record["edit_operation_count"] or 0 for record in records),
        }

    print(json.dumps({
        "format": "composition-pipeline.experiment-result",
        "version": 1,
        "experiment": "labnote_001",
        "model": args.model,
        "summary": summary,
        "cases": results,
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
