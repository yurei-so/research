#!/usr/bin/env python3
"""Reveal and summarize the complete Prosody 017 candidate annotations."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def analyze(session: Path) -> dict[str, Any]:
    bundle = json.loads((session / "annotation-bundle.json").read_text())
    key = json.loads((session / "annotation-key.json").read_text())
    if hashlib.sha256(canonical(bundle).encode()).hexdigest() != key["bundle_sha256"]:
        raise ValueError("bundle does not match reveal key")
    annotations = [json.loads(line) for line in (session / "annotations.jsonl").read_text().splitlines() if line]
    if len(annotations) != len(bundle["items"]):
        raise ValueError("analysis requires a complete annotation session")
    by_id = {row["item_id"]: row for row in annotations}
    items = [{**hidden, "annotation": by_id[hidden["item_id"]]} for hidden in key["items"]]

    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        natural = [row for row in rows if row["annotation"]["naturalness"] >= 4]
        acts = Counter(act for row in natural for act in row["annotation"]["speech_acts"])
        return {"items": len(rows), "natural_items": len(natural),
                "natural_neutral_only": sum(row["annotation"]["speech_acts"] == ["neutral-statement"] for row in natural),
                "natural_speech_acts": dict(sorted(acts.items()))}

    recipes = sorted({row["recipe_id"] for row in items})
    result = {"format": "conversation-prosody.candidate-pool-annotation-result", "version": 1,
              "summary": summary(items),
              "by_recipe": {recipe: summary([row for row in items if row["recipe_id"] == recipe]) for recipe in recipes},
              "items": items}
    output = session / "result.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); output.chmod(0o600)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--session-dir", type=Path, required=True)
    result = analyze(parser.parse_args().session_dir.resolve())
    print(canonical({"summary": result["summary"], "by_recipe": result["by_recipe"]}))


if __name__ == "__main__":
    main()
