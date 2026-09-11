#!/usr/bin/env python3
"""Run the frozen F5-TTS reference-conditioned focus pilot."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import wave

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def digest(value: bytes | str) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()

def plausible_generated_duration(seconds: float) -> bool:
    """Reject empty/truncated/runaway output without scoring reference padding."""
    return 0.8 <= seconds <= 8.0

def execute(protocol_path: Path, manifest_path: Path, reference_dir: Path,
            output_dir: Path, device: str | None) -> dict[str, Any]:
    from f5_tts.api import F5TTS
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("protocol_sha256") != digest(canonical(protocol)):
        raise ValueError("reference manifest does not match frozen protocol")
    expected = {item["reference_file"]: item for item in manifest["references"]}
    for name, item in expected.items():
        if digest((reference_dir / name).read_bytes()) != item["sha256"]:
            raise ValueError(f"reference digest changed: {name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    model = F5TTS(model=protocol["backend"], device=device)
    trials = []
    for pair in protocol["pairs"]:
        for condition in pair["conditions"]:
            reference = reference_dir / condition["reference_file"]
            for seed in protocol["seeds"]:
                trial_id = f"{pair['pair_id']}__{condition['condition_id']}__{seed}"
                output = output_dir / "audio" / f"{trial_id}.wav"
                output.parent.mkdir(parents=True, exist_ok=True)
                model.infer(ref_file=str(reference), ref_text=pair["target"],
                            gen_text=pair["target"], file_wave=str(output), seed=seed,
                            remove_silence=False)
                reference_seconds = duration(reference)
                generated_seconds = duration(output)
                ratio = generated_seconds / reference_seconds
                trials.append({"trial_id": trial_id, "pair_id": pair["pair_id"],
                    "condition_id": condition["condition_id"], "context": condition["context"],
                    "target": pair["target"], "focus": condition["focus"], "seed": seed,
                    "reference_sha256": expected[condition["reference_file"]]["sha256"],
                    "audio_path": str(output.relative_to(output_dir)),
                    "audio_sha256": digest(output.read_bytes()),
                    "reference_duration_seconds": round(reference_seconds, 6),
                    "generated_duration_seconds": round(generated_seconds, 6),
                    "duration_ratio": round(ratio, 6),
                    "passed_integrity": plausible_generated_duration(generated_seconds)})
    hashes = [trial["audio_sha256"] for trial in trials]
    gate_passed = len(trials) == 8 and len(set(hashes)) == 8 \
        and all(trial["passed_integrity"] for trial in trials)
    report = {"format": "conversation-prosody.reference-focus-run", "version": 1,
              "protocol_sha256": manifest["protocol_sha256"], "backend": protocol["backend"],
              "post_processing": "none", "trials": trials, "integrity_gate_passed": gate_passed,
              "integrity_gate": "eight unique WAV files, each 0.8 to 8.0 seconds",
              "listener_review_ready": False,
              "review_blocker": "naturalness and directional-focus checks are required"}
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(canonical({"trials": len(trials), "integrity_gate_passed": gate_passed,
                     "listener_review_ready": False}))
    if not gate_passed:
        raise SystemExit(2)
    return report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("protocol.json"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"])
    args = parser.parse_args()
    execute(args.protocol.resolve(), args.manifest.resolve(), args.reference_dir.resolve(),
            args.output_dir.resolve(), args.device)

if __name__ == "__main__":
    main()
