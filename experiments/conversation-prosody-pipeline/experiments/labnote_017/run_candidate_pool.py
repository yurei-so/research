#!/usr/bin/env python3
"""Generate the frozen twelve-clip Prosody 017 candidate pool."""
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


def validate_protocol(protocol: dict[str, Any]) -> None:
    if protocol.get("format") != "conversation-prosody.candidate-pool":
        raise ValueError("unexpected protocol format")
    if protocol.get("post_processing") != "none" or not isinstance(protocol.get("seed"), int):
        raise ValueError("candidate pool requires a fixed seed and no post-processing")
    recipes, utterances = protocol.get("reading_recipes", []), protocol.get("utterances", [])
    if len(recipes) != 3 or len(utterances) != 4:
        raise ValueError("candidate pool requires three recipes across four utterances")
    for field, rows in (("id", recipes), ("id", utterances)):
        if len({row[field] for row in rows}) != len(rows):
            raise ValueError("candidate pool identifiers must be unique")


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def execute(protocol_path: Path, output_dir: Path, device: str) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    protocol = json.loads(protocol_path.read_text())
    validate_protocol(protocol)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = Qwen3TTSModel.from_pretrained(protocol["backend"], device_map=device,
                                          dtype=torch.bfloat16, attn_implementation="sdpa")
    trials = []
    for utterance in protocol["utterances"]:
        for recipe in protocol["reading_recipes"]:
            seed = protocol["seed"]
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            wavs, sample_rate = model.generate_custom_voice(
                text=utterance["text"], language=protocol["language"],
                speaker=protocol["speaker"], instruct=recipe["instruction"],
                **protocol["generation"])
            if len(wavs) != 1:
                raise RuntimeError("expected exactly one waveform")
            trial_id = f"{utterance['id']}__{recipe['id']}"
            output = output_dir / "audio" / f"{trial_id}.wav"
            output.parent.mkdir(parents=True, exist_ok=True)
            sf.write(output, wavs[0], sample_rate, subtype="PCM_16")
            seconds = duration(output)
            trials.append({"trial_id": trial_id, "utterance_id": utterance["id"],
                           "recipe_id": recipe["id"], "target": utterance["text"],
                           "seed": seed, "instruction_sha256": digest(recipe["instruction"]),
                           "audio_path": str(output.relative_to(output_dir)),
                           "audio_sha256": digest(output.read_bytes()),
                           "duration_seconds": round(seconds, 6),
                           "passed_integrity": 0.8 <= seconds <= 8.0})
    hashes = [row["audio_sha256"] for row in trials]
    gate = len(trials) == 12 and len(set(hashes)) == 12 and all(row["passed_integrity"] for row in trials)
    report = {"format": "conversation-prosody.candidate-pool-run", "version": 1,
              "protocol_sha256": digest(canonical(protocol)), "backend": protocol["backend"],
              "speaker": protocol["speaker"], "post_processing": "none", "trials": trials,
              "integrity_gate_passed": gate}
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(canonical({"trials": len(trials), "integrity_gate_passed": gate}))
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
