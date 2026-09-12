#!/usr/bin/env python3
"""Run the frozen Qwen instruction-form ablation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any
import wave


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("format") != "conversation-prosody.instruction-focus-ablation":
        raise ValueError("unexpected protocol format")
    if protocol.get("arms") != ["positive-only", "context-only"]:
        raise ValueError("unexpected instruction arms")
    if protocol.get("post_processing") != "none" or not isinstance(protocol.get("seed"), int):
        raise ValueError("pilot requires one shared integer seed and no post-processing")
    for pair in protocol.get("pairs", []):
        if len(pair.get("conditions", [])) != 2:
            raise ValueError("each pair requires two focus conditions")
        for condition in pair["conditions"]:
            if condition["focus"].casefold() not in pair["target"].casefold():
                raise ValueError("focus is absent from target")
            if set(condition.get("instructions", {})) != set(protocol["arms"]):
                raise ValueError("condition must define both instruction arms")
            positive = condition["instructions"]["positive-only"].casefold()
            contextual = condition["instructions"]["context-only"].casefold()
            if condition["focus"].casefold() not in positive:
                raise ValueError("positive-only arm must name intended focus")
            if condition["focus"].casefold() in contextual:
                raise ValueError("context-only arm must not name intended focus")


def execute(protocol_path: Path, output_dir: Path, device: str) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    protocol = json.loads(protocol_path.read_text())
    validate_protocol(protocol)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = Qwen3TTSModel.from_pretrained(
        protocol["backend"], device_map=device, dtype=torch.bfloat16,
        attn_implementation="sdpa")
    if protocol["speaker"].casefold() not in {
            value.casefold() for value in model.get_supported_speakers()}:
        raise ValueError("frozen speaker is unsupported")
    trials = []
    for pair in protocol["pairs"]:
        for condition in pair["conditions"]:
            for arm in protocol["arms"]:
                seed = protocol["seed"]
                random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
                instruction = condition["instructions"][arm]
                wavs, sample_rate = model.generate_custom_voice(
                    text=pair["target"], language=protocol["language"],
                    speaker=protocol["speaker"], instruct=instruction,
                    **protocol["generation"])
                if len(wavs) != 1:
                    raise RuntimeError("expected exactly one waveform")
                trial_id = f"{pair['pair_id']}__{condition['condition_id']}__{arm}"
                output = output_dir / "audio" / f"{trial_id}.wav"
                output.parent.mkdir(parents=True, exist_ok=True)
                sf.write(output, wavs[0], sample_rate, subtype="PCM_16")
                seconds = duration(output)
                trials.append({
                    "trial_id": trial_id, "pair_id": pair["pair_id"],
                    "condition_id": condition["condition_id"], "arm": arm,
                    "context": condition["context"], "target": pair["target"],
                    "focus": condition["focus"], "seed": seed,
                    "instruction_sha256": digest(instruction),
                    "audio_path": str(output.relative_to(output_dir)),
                    "audio_sha256": digest(output.read_bytes()),
                    "duration_seconds": round(seconds, 6),
                    "passed_integrity": 0.8 <= seconds <= 8.0})
    hashes = [trial["audio_sha256"] for trial in trials]
    gate = len(trials) == 8 and len(set(hashes)) == 8 \
        and all(trial["passed_integrity"] for trial in trials)
    report = {
        "format": "conversation-prosody.instruction-focus-ablation-run", "version": 1,
        "protocol_sha256": digest(canonical(protocol)), "backend": protocol["backend"],
        "speaker": protocol["speaker"], "post_processing": "none", "trials": trials,
        "integrity_gate_passed": gate, "listener_review_ready": False,
        "review_blocker": "arm-specific naturalness and directional-focus admission required"}
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(canonical({"trials": len(trials), "integrity_gate_passed": gate,
                     "listener_review_ready": False}))
    if not gate:
        raise SystemExit(2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    execute(args.protocol.resolve(), args.output_dir.resolve(), args.device)


if __name__ == "__main__":
    main()
