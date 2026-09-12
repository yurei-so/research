#!/usr/bin/env python3
"""Render the frozen Prosody 018 two-speaker conversation A/B."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("format") != "conversation-prosody.two-speaker-context-ab":
        raise ValueError("unexpected protocol format")
    if protocol.get("arms") != ["isolated", "conversation-aware"]:
        raise ValueError("pilot requires exactly the isolated and conversation-aware arms")
    speakers = protocol.get("speakers", {})
    if len(speakers) != 2 or len(set(speakers.values())) != 2:
        raise ValueError("pilot requires two distinct preset voices")
    turns = protocol.get("scene", {}).get("turns", [])
    if len(turns) != 6 or len({turn.get("id") for turn in turns}) != 6:
        raise ValueError("pilot requires six uniquely identified turns")
    if [turn.get("speaker") for turn in turns] != ["rowan", "mira"] * 3:
        raise ValueError("speakers must alternate for all six turns")
    for turn in turns:
        if turn.get("speaker") not in speakers:
            raise ValueError("turn references an unknown speaker")
        if not str(turn.get("text", "")).strip() or not str(turn.get("context_instruction", "")).strip():
            raise ValueError("every turn requires text and context-aware direction")
        gap = turn.get("gap_after_ms")
        if not isinstance(gap, int) or not 0 <= gap <= 1000:
            raise ValueError("turn gaps must be integer milliseconds between zero and 1000")
    if protocol.get("post_processing") != "silence-only assembly":
        raise ValueError("generated speech may not be edited")


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
    supported = {speaker.casefold() for speaker in model.get_supported_speakers()}
    if any(voice.casefold() not in supported for voice in protocol["speakers"].values()):
        raise ValueError("frozen preset voice is unsupported by the installed model")

    trials: list[dict[str, Any]] = []
    conversations: list[dict[str, Any]] = []
    for arm_index, arm in enumerate(protocol["arms"]):
        assembled: list[Any] = []
        sample_rate: int | None = None
        for turn_index, turn in enumerate(protocol["scene"]["turns"]):
            seed = protocol["seed"] + turn_index
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            instruction = (protocol["isolated_instruction"] if arm == "isolated"
                           else turn["context_instruction"])
            wavs, current_rate = model.generate_custom_voice(
                text=turn["text"], language=protocol["language"],
                speaker=protocol["speakers"][turn["speaker"]], instruct=instruction,
                **protocol["generation"])
            if len(wavs) != 1 or (sample_rate is not None and current_rate != sample_rate):
                raise RuntimeError("expected one waveform per turn at one shared sample rate")
            sample_rate = current_rate
            waveform = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
            trial_id = f"{arm}__{turn['id']}"
            output = output_dir / "turns" / f"{trial_id}.wav"
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(output, waveform, sample_rate, subtype="PCM_16")
            seconds = len(waveform) / sample_rate
            trials.append({
                "trial_id": trial_id, "arm": arm, "turn_id": turn["id"],
                "speaker_role": turn["speaker"], "preset_voice": protocol["speakers"][turn["speaker"]],
                "seed": seed, "text_sha256": digest(turn["text"]),
                "instruction_sha256": digest(instruction),
                "audio_path": str(output.relative_to(output_dir)),
                "audio_sha256": digest(output.read_bytes()),
                "duration_seconds": round(seconds, 6),
                "passed_integrity": 0.6 <= seconds <= 10.0,
            })
            assembled.append(waveform)
            gap_samples = round(sample_rate * turn["gap_after_ms"] / 1000)
            if gap_samples:
                assembled.append(np.zeros(gap_samples, dtype=np.float32))
        assert sample_rate is not None
        conversation = np.concatenate(assembled)
        conversation_path = output_dir / "conversations" / f"{arm}.wav"
        conversation_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(conversation_path, conversation, sample_rate, subtype="PCM_16")
        conversations.append({
            "arm": arm, "audio_path": str(conversation_path.relative_to(output_dir)),
            "audio_sha256": digest(conversation_path.read_bytes()),
            "duration_seconds": round(len(conversation) / sample_rate, 6),
        })

    hashes = [trial["audio_sha256"] for trial in trials]
    gate = (len(trials) == 12 and len(set(hashes)) == 12
            and all(trial["passed_integrity"] for trial in trials)
            and all(5 <= row["duration_seconds"] <= 60 for row in conversations))
    report = {
        "format": "conversation-prosody.two-speaker-context-ab-run", "version": 1,
        "protocol_sha256": digest(canonical(protocol)), "backend": protocol["backend"],
        "post_processing": protocol["post_processing"], "trials": trials,
        "conversations": conversations, "integrity_gate_passed": gate,
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report_path.chmod(0o600)
    print(canonical({"trials": len(trials), "conversations": conversations,
                     "integrity_gate_passed": gate}))
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

