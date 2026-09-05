#!/usr/bin/env python3
"""Prepare a private audio-v2 review from a passing Labnote 008 gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def private_json(path: Path, value: Any) -> None:
    path.write_text(canonical(value) + "\n")
    path.chmod(0o600)


def prepare(source_run: Path, gate_dir: Path, output_dir: Path,
            calibration_audio: Path) -> dict[str, Any]:
    report = json.loads((gate_dir / "report.json").read_text())
    if not report.get("gate_passed") or not report.get("trials") \
            or not all(trial["metrics"]["passed"] for trial in report["trials"]):
        raise ValueError("listener review requires a passing acoustic gate")
    if digest(canonical(report["protocol"])) != report["protocol_digest"]:
        raise ValueError("protocol digest mismatch")
    corpus = {case["case_id"]: case for case in
              json.loads((source_run / "corpus.json").read_text())}
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets_dir.chmod(0o700)
    assets, pairs, reveal = [], [], []

    def copy_asset(source: Path, asset_id: str, expected: str | None = None) -> str:
        content = source.read_bytes()
        actual = digest(content)
        if expected is not None and actual != expected:
            raise ValueError("qualified audio digest mismatch")
        file_name = f"{asset_id}.wav"
        target = assets_dir / file_name
        shutil.copyfile(source, target); target.chmod(0o600)
        assets.append({"asset_id": asset_id, "file_name": file_name,
                       "sha256": actual, "media_type": "audio/wav"})
        return asset_id

    calibration_id = copy_asset(calibration_audio, "calibration")
    for index, trial in enumerate(sorted(report["trials"], key=lambda item: item["trial_id"])):
        context_index = int(digest(f"labnote-008-context:{trial['trial_id']}")[-1], 16) % 2
        intended_case = corpus[trial["case_ids"][context_index]]
        asset_ids = [copy_asset(gate_dir / path, f"clip-{index:02d}-{side}", expected)
                     for side, (path, expected) in enumerate(
                         zip(trial["audio_paths"], trial["audio_sha256"]))]
        intended_side = context_index
        a_side = int(digest(f"labnote-008-order:{trial['trial_id']}")[-1], 16) % 2
        b_side = 1 - a_side
        pair_id = digest(f"{report['protocol_digest']}:{trial['trial_id']}")[:24]
        pairs.append({
            "pair_id": pair_id, "case_id": intended_case["case_id"],
            "prompt_style": "contrastive-emphasis", "repetition": index + 1,
            "task": "Which delivery better matches the stated conversational context?",
            "draft": f"Context: {intended_case['context']}\n\nSpoken text: {intended_case['target']}",
            "candidate_a_asset": asset_ids[a_side], "candidate_b_asset": asset_ids[b_side],
            "criteria": ["naturalness"],
        })
        reveal.append({
            "pair_id": pair_id,
            "candidate_a_arm": "intended_focus" if a_side == intended_side else "alternate_focus",
            "candidate_b_arm": "intended_focus" if b_side == intended_side else "alternate_focus",
        })
    campaign_digest = digest(canonical({
        "protocol_digest": report["protocol_digest"],
        "trials": [{"trial_id": trial["trial_id"], "audio_sha256": trial["audio_sha256"]}
                   for trial in sorted(report["trials"], key=lambda item: item["trial_id"])],
    }))
    bundle = {"format": "composition-pipeline.blinded-review", "version": 2,
              "campaign_digest": campaign_digest, "mode": "audio",
              "calibration_asset": calibration_id, "assets": assets, "pairs": pairs}
    key = {"format": "composition-pipeline.blinded-review-key", "version": 2,
           "campaign_digest": campaign_digest, "review_bundle_digest": digest(canonical(bundle)),
           "baseline_arm": "intended_focus", "treatment_arm": "alternate_focus",
           "pairs": reveal}
    private_json(output_dir / "review-bundle.json", bundle)
    private_json(output_dir / "review-key.json", key)
    intake = {"format": "conversation-prosody.focus-review-intake", "version": 1,
              "protocol_digest": report["protocol_digest"], "qualified_trials": len(pairs),
              "campaign_digest": campaign_digest,
              "review_bundle_digest": key["review_bundle_digest"]}
    private_json(output_dir / "review-intake.json", intake)
    return intake


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--gate-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration-audio", type=Path, required=True)
    args = parser.parse_args()
    print(canonical(prepare(args.source_run.resolve(), args.gate_dir.resolve(),
                            args.output_dir.resolve(), args.calibration_audio.resolve())))


if __name__ == "__main__":
    main()
