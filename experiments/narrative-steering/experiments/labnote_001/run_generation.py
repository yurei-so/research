#!/usr/bin/env python3
"""Resumable, digest-pinned Ollama generation for narrative-steering-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODELS = {
    "qwen3:8b": "500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41",
    "gemma3:12b": "f4031aab637d1ffa37b42570452ae0e4fad0314754d17ded67322e4b95836f8a",
    "llama3.2:latest": "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72",
}
SEEDS = (2026090501, 2026090502)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def request_json(url: str, payload: dict[str, Any] | None, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, data=None if payload is None else canonical(payload),
        headers={"content-type": "application/json"}, method="GET" if payload is None else "POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise RuntimeError("Ollama returned a non-object response")
    return value


def prompt(case: dict[str, Any], instruction: str) -> str:
    return ("Write only the requested story continuation. Do not explain your choices, add a heading, "
        "or mention these instructions.\n\nSTORY STATE\n" +
        json.dumps(case, ensure_ascii=False, indent=2) + "\n\nINSTRUCTION\n" + instruction)


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def run(endpoint: str, output: Path, timeout: int) -> None:
    here = Path(__file__).resolve().parent
    protocol = json.loads((here / "frozen-protocol.json").read_text())
    corpus = json.loads((here / "corpus.json").read_text())
    protocol_hash = digest({"protocol": protocol, "corpus": corpus})
    installed = {item["name"]: item.get("digest") for item in request_json(f"{endpoint}/api/tags", None, timeout).get("models", [])}
    drift = [name for name, expected in MODELS.items() if installed.get(name) != expected]
    if drift:
        raise RuntimeError("missing or digest-mismatched frozen models: " + ", ".join(drift))
    identities = {name: f"ollama:{name}@sha256:{model_digest}" for name, model_digest in MODELS.items()}
    state = {"format": "narrative-steering.generations", "version": 1,
        "protocol_digest": protocol_hash, "models": list(identities.values()), "records": []}
    if output.exists():
        state = json.loads(output.read_text())
        if state.get("protocol_digest") != protocol_hash or state.get("models") != list(identities.values()):
            raise RuntimeError("existing generation checkpoint does not match the frozen run")
    completed = {(row["model_id"], row["case_id"], row["variant_id"], row["sample_id"]) for row in state["records"]}
    total = len(MODELS) * len(corpus["cases"]) * len(corpus["prompt_variants"]) * len(SEEDS)
    for name, model_id in identities.items():
        for case in corpus["cases"]:
            for variant in corpus["prompt_variants"]:
                for sample_id, seed in enumerate(SEEDS, 1):
                    key = (model_id, case["id"], variant["id"], sample_id)
                    if key in completed:
                        continue
                    started = time.monotonic()
                    response = request_json(f"{endpoint}/api/generate", {
                        "model": name, "stream": False, "think": False,
                        "prompt": prompt(case, variant["instruction"]),
                        "options": {"temperature": protocol["generation"]["temperature"],
                            "top_p": protocol["generation"]["top_p"], "seed": seed,
                            "num_predict": protocol["generation"]["max_output_tokens"]},
                    }, timeout)
                    text = response.get("response")
                    if not isinstance(text, str) or not text.strip():
                        raise RuntimeError(f"empty response for {key}")
                    state["records"].append({"model_id": model_id, "case_id": case["id"],
                        "variant_id": variant["id"], "sample_id": sample_id, "text": text.strip(),
                        "seed": seed, "runtime_model": name, "runtime_digest": MODELS[name],
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                        "eval_count": response.get("eval_count"), "generated_at": datetime.now(timezone.utc).isoformat()})
                    atomic_write(output, state)
                    print(f"[{len(state['records'])}/{total}] {name} {case['id']} {variant['id']} sample {sample_id}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://10.0.0.182:11434")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    run(args.endpoint.rstrip("/"), args.output.resolve(), args.timeout)
