#!/usr/bin/env python3
"""Reveal and summarize a complete Prosody 015 annotation session."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def normalized_phrases(value: str) -> set[str]:
    return {re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
            for part in value.split(",") if part.strip()}


def analyze(session_dir: Path) -> dict[str, Any]:
    bundle = json.loads((session_dir / "annotation-bundle.json").read_text())
    key = json.loads((session_dir / "annotation-key.json").read_text())
    if hashlib.sha256(canonical(bundle).encode()).hexdigest() != key["bundle_sha256"]:
        raise ValueError("bundle does not match reveal key")
    annotations = [json.loads(line) for line in
                   (session_dir / "annotations.jsonl").read_text().splitlines() if line]
    if len(annotations) != len(bundle["items"]):
        raise ValueError("analysis requires a complete annotation session")
    by_id = {row["item_id"]: row for row in annotations}
    if len(by_id) != len(annotations):
        raise ValueError("duplicate annotation item")

    revealed = []
    for hidden in key["items"]:
        annotation = by_id.get(hidden["item_id"])
        if annotation is None:
            raise ValueError("annotation and reveal item sets differ")
        requested = re.sub(r"[^a-z0-9]+", " ", hidden["focus"].lower()).strip()
        revealed.append({**hidden, "annotation": annotation,
                         "requested_focus_named": requested in normalized_phrases(
                             annotation["perceived_focus"])})

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        count = len(rows)
        acts = Counter(act for row in rows for act in row["annotation"]["speech_acts"])
        affects = Counter(affect for row in rows for affect in row["annotation"]["affects"])
        return {
            "items": count,
            "requested_focus_named": sum(row["requested_focus_named"] for row in rows),
            "naturalness_at_least_4": sum(row["annotation"]["naturalness"] >= 4 for row in rows),
            "mean_naturalness": round(sum(row["annotation"]["naturalness"] for row in rows) / count, 3),
            "mean_confidence": round(sum(row["annotation"]["confidence"] for row in rows) / count, 3),
            "speech_acts": dict(sorted(acts.items())),
            "affects": dict(sorted(affects.items())),
        }

    arms = sorted({row["arm"] for row in revealed})
    return {
        "format": "conversation-prosody.emergent-reading-annotation-result",
        "version": 1,
        "bundle_sha256": key["bundle_sha256"],
        "summary": summarize(revealed),
        "by_arm": {arm: summarize([row for row in revealed if row["arm"] == arm]) for arm in arms},
        "items": revealed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.session_dir.resolve())
    output = args.output.resolve() if args.output else args.session_dir.resolve() / "result.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    print(canonical(result["summary"]))


if __name__ == "__main__":
    main()
