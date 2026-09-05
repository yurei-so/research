#!/usr/bin/env python3
"""Prepare a bounded, private, blinded listener slice from oracle synthesis."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


PROTOCOL = {
    "format": "conversation-prosody.listener-protocol",
    "version": 1,
    "experiment": "labnote_004_stage_b_listener_slice",
    "selection": "minimum_sha256_per_phenomenon",
    "phenomena": 11,
    "readings_per_selected_pair": 2,
    "voice_assignment": "balanced_sha256_rank",
    "conditions": ["gold", "swapped"],
    "identical_audio": "automatic_tie",
    "duplicate_audio_pairs": "one_manual_representative",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_private(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(f"{canonical(value)}\n")
    path.chmod(0o600)


def prepare(run_dir: Path, output_dir: Path, calibration_audio: Path) -> dict[str, Any]:
    corpus = json.loads((run_dir / "corpus.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text().splitlines() if line]
    by_case = {case["case_id"]: case for case in corpus}
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in corpus:
        pairs[case["pair_id"]].append(case)
    phenomena: dict[str, list[str]] = defaultdict(list)
    for pair_id, cases in pairs.items():
        if len(cases) != 2 or len({case["target"] for case in cases}) != 1:
            raise ValueError("invalid authored contrast pair")
        phenomena[cases[0]["phenomenon"]].append(pair_id)
    if len(phenomena) != 11:
        raise ValueError("listener slice requires exactly eleven phenomena")
    selected = {
        phenomenon: min(pair_ids, key=lambda pair_id: sha256_bytes(
            f"labnote-004-listener-v1:{pair_id}".encode()))
        for phenomenon, pair_ids in phenomena.items()
    }
    ranked_phenomena = sorted(selected, key=lambda value: sha256_bytes(
        f"labnote-004-voice-v1:{value}".encode()))
    voice_by_phenomenon = {
        phenomenon: "af_heart" if index < 6 else "am_adam"
        for index, phenomenon in enumerate(ranked_phenomena)
    }
    row_lookup = {(row["case_id"], row["voice"], row["condition"]): row for row in rows}
    campaign_digest = sha256_bytes(canonical(PROTOCOL).encode())
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets_dir.chmod(0o700)
    assets, review_pairs, reveal = [], [], []
    audio_pair_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    automatic_ties = 0

    def add_asset(source: Path, asset_id: str) -> str:
        content = source.read_bytes()
        file_name = f"{asset_id}.wav"
        target = assets_dir / file_name
        target.write_bytes(content); target.chmod(0o600)
        assets.append({"asset_id": asset_id, "file_name": file_name,
            "sha256": sha256_bytes(content), "media_type": "audio/wav"})
        return asset_id

    calibration_id = add_asset(calibration_audio, "calibration")
    candidates = []
    for phenomenon, pair_id in sorted(selected.items()):
        voice = voice_by_phenomenon[phenomenon]
        for case in sorted(pairs[pair_id], key=lambda item: item["reading"]):
            condition_rows = {condition: row_lookup[(case["case_id"], voice, condition)]
                for condition in ("gold", "swapped")}
            content = {}
            for condition, row in condition_rows.items():
                source = (run_dir / row["audio_path"]).resolve()
                if not source.is_relative_to(run_dir.resolve()) or not source.is_file():
                    raise ValueError("unsafe or missing synthesis audio")
                value = source.read_bytes()
                if sha256_bytes(value) != row["audio_sha256"]:
                    raise ValueError("synthesis audio digest mismatch")
                content[condition] = value
            if content["gold"] == content["swapped"]:
                automatic_ties += 1
                continue
            unordered_digest = sha256_bytes(b"\0".join(sorted((content["gold"], content["swapped"]))))
            audio_pair_groups[unordered_digest].append({"case": case, "voice": voice,
                "content": content})

    for unordered_digest, occurrences in sorted(audio_pair_groups.items()):
        item = occurrences[0]; case = item["case"]; voice = item["voice"]
        pair_id = sha256_bytes(f"{campaign_digest}:{unordered_digest}".encode())[:24]
        condition_assets = {}
        for condition in ("gold", "swapped"):
            asset_id = f"clip-{len(assets):03d}"
            file_name = f"{asset_id}.wav"; target = assets_dir / file_name
            value = item["content"][condition]
            target.write_bytes(value); target.chmod(0o600)
            assets.append({"asset_id": asset_id, "file_name": file_name,
                "sha256": sha256_bytes(value), "media_type": "audio/wav"})
            condition_assets[condition] = asset_id
        gold_first = int(pair_id[-1], 16) % 2 == 0
        a_condition, b_condition = ("gold", "swapped") if gold_first else ("swapped", "gold")
        review_pairs.append({"pair_id": pair_id, "case_id": case["case_id"],
            "prompt_style": case["phenomenon"], "repetition": int(case["reading"]),
            "task": "Which delivery better matches the stated conversational context?",
            "draft": f"Context: {case['context']}\n\nSpoken text: {case['target']}",
            "candidate_a_asset": condition_assets[a_condition],
            "candidate_b_asset": condition_assets[b_condition], "criteria": ["naturalness"]})
        reveal.append({"pair_id": pair_id,
            "candidate_a_arm": "intended_delivery" if a_condition == "gold" else "swapped_delivery",
            "candidate_b_arm": "intended_delivery" if b_condition == "gold" else "swapped_delivery"})

    bundle = {"format": "composition-pipeline.blinded-review", "version": 2,
        "campaign_digest": campaign_digest, "mode": "audio",
        "calibration_asset": calibration_id, "assets": assets, "pairs": review_pairs}
    bundle_digest = sha256_bytes(canonical(bundle).encode())
    key = {"format": "composition-pipeline.blinded-review-key", "version": 2,
        "campaign_digest": campaign_digest, "review_bundle_digest": bundle_digest,
        "baseline_arm": "intended_delivery", "treatment_arm": "swapped_delivery",
        "pairs": reveal}
    group_sizes = sorted((len(items) for items in audio_pair_groups.values()), reverse=True)
    intake = {"format": "conversation-prosody.listener-intake", "version": 1,
        "campaign_digest": campaign_digest, "selected_authored_pairs": len(selected),
        "selected_readings": sum(len(pairs[pair_id]) for pair_id in selected.values()),
        "automatic_ties": automatic_ties, "changed_audio_trials": sum(group_sizes),
        "unique_review_pairs": len(review_pairs),
        "duplicate_changed_trials": sum(size - 1 for size in group_sizes),
        "duplicate_group_size_counts": dict(sorted(Counter(group_sizes).items())),
        "voice_counts": dict(sorted(Counter(voice_by_phenomenon.values()).items())),
        "phenomena": sorted(selected), "bundle_digest": bundle_digest}
    write_private(output_dir / "review-bundle.json", bundle)
    write_private(output_dir / "review-key.json", key)
    write_private(output_dir / "listener-intake.json", intake)
    return intake


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration-audio", type=Path, required=True)
    args = parser.parse_args()
    print(canonical(prepare(args.run_dir.resolve(), args.output_dir.resolve(),
        args.calibration_audio.resolve())))


if __name__ == "__main__":
    main()
