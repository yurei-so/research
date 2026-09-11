#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from voxel_guidance import evaluate_model_encodings

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"task": {"type": "string", "enum": ["acquire", "construct", "explore", "recover"]}},
    "required": ["task"],
    "additionalProperties": False,
}

parser = argparse.ArgumentParser(description="Run the frozen local-model encoding comparison")
parser.add_argument("--session-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--host", default="http://127.0.0.1:11434")
parser.add_argument("--model", default="qwen3:8b")
parser.add_argument("--seed", type=int, default=1701)
parser.add_argument("--repetitions", type=int, default=1)
args = parser.parse_args()
if args.repetitions < 1 or args.repetitions > 10:
    raise SystemExit("repetitions must be between 1 and 10")


def request(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    with urlopen(Request(args.host.rstrip("/") + path, data=data, headers=headers), timeout=180) as response:
        return json.load(response)


models = request("/api/tags")["models"]
metadata = next((item for item in models if item["name"] == args.model), None)
if metadata is None:
    raise SystemExit(f"model is not installed: {args.model}")

# Warm the model before descriptive timing. The warm-up is not scored.
request("/api/generate", {"model": args.model, "prompt": "Reply with OK.", "stream": False,
                          "think": False, "options": {"temperature": 0, "seed": args.seed, "num_predict": 4}})


def generate(prompt: str) -> dict:
    response = request("/api/generate", {
        "model": args.model, "prompt": prompt, "stream": False, "think": False,
        "format": OUTPUT_SCHEMA,
        "options": {"temperature": 0, "seed": args.seed, "num_predict": 32},
    })
    parsed = json.loads(response["response"])
    return {"task": parsed["task"], "prompt_eval_count": response["prompt_eval_count"],
            "total_duration_ns": response["total_duration"]}


sessions = []
for path in sorted(args.session_root.glob("*.ndjson")):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if rows:
        sessions.append(rows)

runs = [evaluate_model_encodings(sessions, generate, model=args.model,
                                 model_digest=metadata["digest"], seed=args.seed)
        for _ in range(args.repetitions)]
result = runs[0]
if len(runs) > 1:
    result["repeat_check"] = {
        "run_count": len(runs),
        "accuracy_by_representation": {
            name: [run["results"][name]["accuracy"] for run in runs]
            for name in result["results"]
        },
        "confusion_identical": {
            name: all(run["results"][name]["confusion"] == runs[0]["results"][name]["confusion"]
                      for run in runs[1:])
            for name in result["results"]
        },
        "prompt_tokens_identical": {
            name: all(run["results"][name]["prompt_tokens"] == runs[0]["results"][name]["prompt_tokens"]
                      for run in runs[1:])
            for name in result["results"]
        },
        "note": "Temperature zero and a fixed seed do not guarantee backend-level determinism.",
    }
args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
