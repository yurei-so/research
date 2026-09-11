#!/usr/bin/env python3
"""Blinded candidate scorer. Its output requires held-out human calibration."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any

SCORER = "deepseek-r1:8b"
SCORER_DIGEST = "6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763"


def request(url: str, payload: dict[str, Any] | None, timeout: int) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    req = urllib.request.Request(url, data=data, headers={"content-type": "application/json"},
        method="GET" if data is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def write_private(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600); os.replace(temporary, path)


def run(endpoint: str, bundle_path: Path, output: Path, timeout: int) -> None:
    bundle = json.loads(bundle_path.read_text())
    available = {item["name"]: item.get("digest") for item in request(f"{endpoint}/api/tags", None, timeout).get("models", [])}
    if available.get(SCORER) != SCORER_DIGEST:
        raise RuntimeError("automated scorer is missing or digest-mismatched")
    state = {"format": "narrative-steering.automated-judgments", "version": 1,
        "bundle_digest": bundle["bundle_digest"], "scorer": f"ollama:{SCORER}@sha256:{SCORER_DIGEST}", "judgments": []}
    if output.exists():
        state = json.loads(output.read_text())
        if state.get("bundle_digest") != bundle["bundle_digest"]:
            raise RuntimeError("existing scorer checkpoint belongs to another bundle")
    done = {item["item_id"] for item in state["judgments"]}
    dimensions = bundle["items"][0]["dimensions"]
    schema = {"type": "object", "properties": {
        "scores": {"type": "object", "properties": {name: {"type": "integer", "minimum": -2, "maximum": 2}
            for name in dimensions}, "required": dimensions, "additionalProperties": False},
        "confidence": {"type": "integer", "minimum": 1, "maximum": 3}},
        "required": ["scores", "confidence"], "additionalProperties": False}
    for item in bundle["items"]:
        if item["item_id"] in done:
            continue
        anchors = "\n".join(f"- {name}: -2 = {item['anchors'][name]['negative']}; 0 = no material push; +2 = {item['anchors'][name]['positive']}"
            for name in dimensions)
        prompt = ("Act as a strict narrative measurement instrument. Score only the continuation's directional change from the supplied state. "
            "Do not rate prose quality. Use integer scores and reserve +/-2 for strong clear steering.\n\nSTATE\n" +
            json.dumps(item["story_state"], indent=2) + "\n\nINSTRUCTION\n" + item["instruction"] +
            "\n\nCONTINUATION\n" + item["continuation"] + "\n\nRUBRIC\n" + anchors)
        response = request(f"{endpoint}/api/generate", {"model": SCORER, "stream": False, "think": False,
            "format": schema, "prompt": prompt, "options": {"temperature": 0, "seed": 20260905, "num_predict": 180}}, timeout)
        value = json.loads(response["response"])
        if (set(value.get("scores", {})) != set(dimensions)
                or any(type(score) is not int or score < -2 or score > 2 for score in value["scores"].values())
                or type(value.get("confidence")) is not int or not 1 <= value["confidence"] <= 3):
            raise RuntimeError(f"invalid scorer output for {item['item_id']}")
        state["judgments"].append({"item_id": item["item_id"], "scores": value["scores"], "confidence": value["confidence"]})
        write_private(output, state)
        print(f"[{len(state['judgments'])}/{len(bundle['items'])}] {item['item_id']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    run(args.endpoint.rstrip("/"), args.bundle.resolve(), args.output.resolve(), args.timeout)
