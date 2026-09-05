#!/usr/bin/env python3
"""Run the bounded whole-utterance Kokoro native-stress pilot."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any


VOICES = ("af_heart", "am_adam")
PROTOCOL = {
    "format": "conversation-prosody.native-stress-pilot",
    "version": 1,
    "selection": "two_minimum_sha256_pairs_after_both_focus_words_primary_g2p_gate",
    "voices": list(VOICES),
    "conditions": "intended_primary_competing_secondary",
    "misaki_annotation": "[competing_focus](-1)",
    "post_processing": "none",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def annotate_competing_focus(target: str, focus: str) -> str:
    pattern = re.compile(rf"(?<![A-Za-z0-9']){re.escape(focus)}(?![A-Za-z0-9'])", re.IGNORECASE)
    matches = list(pattern.finditer(target))
    if len(matches) != 1:
        raise ValueError("focus span must occur exactly once as a whole token")
    match = matches[0]
    return f"{target[:match.start()]}[{match.group()}](-1){target[match.end():]}"


def token_map(tokens: list[Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for token in tokens:
        if token.phonemes:
            result[token.text.casefold()].append(token.phonemes)
    return dict(result)


def validate_phoneme_contrast(plain_tokens: list[Any], variant_tokens: list[Any],
                              intended_focus: str, competing_focus: str) -> dict[str, Any]:
    plain, variant = token_map(plain_tokens), token_map(variant_tokens)
    intended_key, competing_key = intended_focus.casefold(), competing_focus.casefold()
    if set(plain) != set(variant) or any(len(plain[key]) != len(variant[key]) for key in plain):
        raise ValueError("stress annotation changed token topology")
    changed = []
    for key in plain:
        for index, (before, after) in enumerate(zip(plain[key], variant[key])):
            if before != after:
                changed.append((key, index, before, after))
    if len(plain.get(intended_key, [])) != 1 or len(plain.get(competing_key, [])) != 1:
        raise ValueError("focus tokens must each resolve exactly once")
    if plain[intended_key][0] != variant[intended_key][0] or "ˈ" not in plain[intended_key][0]:
        raise ValueError("intended primary stress was not preserved")
    before, after = plain[competing_key][0], variant[competing_key][0]
    if "ˈ" not in before or "ˌ" not in after or "ˈ" in after:
        raise ValueError("competing focus was not demoted to secondary stress")
    if changed != [(competing_key, 0, before, after)]:
        raise ValueError("stress annotation changed non-competing phonemes")
    return {"intended_focus": intended_focus, "competing_focus": competing_focus,
            "competing_before": before, "competing_after": after,
            "changed_token_count": len(changed)}


def execute(source_run: Path, output_dir: Path) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    corpus = json.loads((source_run / "corpus.json").read_text())
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in corpus:
        if case["phenomenon"] == "contrastive-emphasis":
            pairs[case["pair_id"]].append(case)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    eligible = []
    for pair_id, readings in pairs.items():
        if len(readings) != 2 or len({case["target"] for case in readings}) != 1:
            continue
        _phonemes, tokens = pipeline.g2p(readings[0]["target"])
        mapped = token_map(tokens)
        focuses = [case["gold_ir"]["focus_span"].casefold() for case in readings]
        if all(len(mapped.get(focus, [])) == 1 and "ˈ" in mapped[focus][0]
               for focus in focuses):
            eligible.append(pair_id)
    if len(eligible) < 2:
        raise ValueError("fewer than two authored pairs passed the primary-stress eligibility gate")
    selected = sorted(eligible, key=lambda pair_id: digest(f"labnote-009:{pair_id}"))[:2]
    output_dir.mkdir(parents=True, exist_ok=True)
    trials = []
    for pair_id in selected:
        readings = sorted(pairs[pair_id], key=lambda case: case["reading"])
        if len(readings) != 2 or len({case["target"] for case in readings}) != 1:
            raise ValueError("invalid authored contrast pair")
        plain_phonemes, plain_tokens = pipeline.g2p(readings[0]["target"])
        conditions = []
        for index, reading in enumerate(readings):
            competing = readings[1 - index]["gold_ir"]["focus_span"]
            annotated = annotate_competing_focus(reading["target"], competing)
            phonemes, tokens = pipeline.g2p(annotated)
            manifest = validate_phoneme_contrast(
                plain_tokens, tokens, reading["gold_ir"]["focus_span"], competing)
            conditions.append({"case": reading, "annotated": annotated,
                               "phonemes": phonemes, "manifest": manifest})
        for voice in VOICES:
            audio_paths, audio_hashes, durations = [], [], []
            for condition in conditions:
                results = list(pipeline.generate_from_tokens(
                    condition["phonemes"], voice=voice, speed=1.0))
                if len(results) != 1 or results[0].audio is None:
                    raise RuntimeError("Kokoro returned an unexpected result count")
                audio = np.asarray(results[0].audio.detach().cpu().numpy()
                                   if hasattr(results[0].audio, "detach") else results[0].audio,
                                   dtype=np.float32).reshape(-1)
                path = output_dir / "audio" / voice / f"{condition['case']['case_id']}.wav"
                path.parent.mkdir(parents=True, exist_ok=True)
                sf.write(path, audio, 24_000, subtype="PCM_16")
                audio_paths.append(str(path.relative_to(output_dir)))
                audio_hashes.append(digest(path.read_bytes()))
                durations.append(len(audio) / 24_000)
            duration_delta = abs(durations[0] - durations[1]) / max(durations)
            passed = audio_hashes[0] != audio_hashes[1] and duration_delta <= 0.20
            trials.append({
                "trial_id": digest(f"{pair_id}:{voice}")[:24], "pair_id": pair_id,
                "voice": voice, "case_ids": [item["case"]["case_id"] for item in conditions],
                "contexts": [item["case"]["context"] for item in conditions],
                "target": readings[0]["target"],
                "focus_spans": [item["case"]["gold_ir"]["focus_span"] for item in conditions],
                "phoneme_manifests": [item["manifest"] for item in conditions],
                "phoneme_sha256": [digest(item["phonemes"]) for item in conditions],
                "audio_paths": audio_paths, "audio_sha256": audio_hashes,
                "durations_seconds": durations, "duration_delta_ratio": duration_delta,
                "passed": passed,
            })
    report = {"format": PROTOCOL["format"], "version": PROTOCOL["version"],
              "protocol": PROTOCOL, "protocol_digest": digest(canonical(PROTOCOL)),
              "selected_pairs": selected, "trials": trials,
              "passed_trials": sum(trial["passed"] for trial in trials),
              "gate_passed": bool(trials) and all(trial["passed"] for trial in trials)}
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(canonical({"gate_passed": report["gate_passed"],
                     "passed_trials": report["passed_trials"],
                     "trials": len(trials), "protocol_digest": report["protocol_digest"]}))
    if not report["gate_passed"]:
        raise SystemExit(2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    execute(args.source_run.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
