#!/usr/bin/env python3
"""Measure whether native Kokoro stress creates directional word prominence."""

from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import math
from statistics import median
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "labnote_009"))
from run_native_stress import annotate_competing_focus, canonical, digest, token_map, validate_phoneme_contrast  # noqa: E402

VOICES = ("af_heart", "am_adam")
PROTOCOL = {"format": "conversation-prosody.native-stress-prominence", "version": 1,
    "voices": list(VOICES), "eligible_pairs": "both_focus_words_primary_under_plain_g2p",
    "word_gate": {"minimum_dimensions": 2, "minimum_ratio": 1.03, "minimum_any_ratio": 0.90},
    "campaign_gate": {"minimum_trials": 5, "minimum_per_voice": 2}, "post_processing": "none"}

def rms(values: array) -> float:
    return math.sqrt(sum(value * value for value in values) / max(len(values), 1))

def median_f0(values: array) -> float:
    estimates=[]
    for start in range(0,max(0,len(values)-960+1),240):
        frame=values[start:start+960]; mean=sum(frame)/960; centered=[v-mean for v in frame]
        energy=sum(v*v for v in centered)
        if energy < 1: continue
        scores=[]
        for lag in range(60,480):
            scores.append(sum(centered[i]*centered[i+lag] for i in range(960-lag))/energy)
        best=max(range(len(scores)),key=scores.__getitem__)
        if scores[best]>=0.35: estimates.append(24000/(60+best))
    return median(estimates) if estimates else 0.0


def samples(value: Any) -> array:
    if hasattr(value, "detach"): value = value.detach().cpu().numpy()
    return array("h", (max(-32768, min(32767, round(float(x) * 32767))) for x in value))


def token_window(tokens: list[Any], focus: str) -> tuple[float, float]:
    found = [t for t in tokens if t.text.casefold() == focus.casefold()]
    if len(found) != 1 or found[0].start_ts is None or found[0].end_ts is None:
        raise ValueError("focus token timestamp unavailable")
    return float(found[0].start_ts), float(found[0].end_ts)


def cut(audio: array, window: tuple[float, float]) -> array:
    return audio[round(window[0] * 24000):round(window[1] * 24000)]


def word_metrics(primary_audio: array, primary_window: tuple[float, float],
                 secondary_audio: array, secondary_window: tuple[float, float]) -> dict[str, Any]:
    p, s = cut(primary_audio, primary_window), cut(secondary_audio, secondary_window)
    ratios = {"energy_ratio": rms(p) / max(rms(s), 1),
              "duration_ratio": len(p) / max(len(s), 1),
              "f0_ratio": median_f0(p) / max(median_f0(s), 1e-9)}
    directional = sum(value >= 1.03 for value in ratios.values())
    return {**ratios, "directional_dimensions": directional,
            "passed": directional >= 2 and min(ratios.values()) >= 0.90}


def execute(source_run: Path, output_dir: Path) -> dict[str, Any]:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    corpus = json.loads((source_run / "corpus.json").read_text())
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in corpus:
        if case["phenomenon"] == "contrastive-emphasis": pairs[case["pair_id"]].append(case)
    pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    eligible = []
    for pair_id, readings in pairs.items():
        _ps, tokens = pipeline.g2p(readings[0]["target"]); mapped = token_map(tokens)
        focuses = [case["gold_ir"]["focus_span"].casefold() for case in readings]
        if all(len(mapped.get(f, [])) == 1 and "ˈ" in mapped[f][0] for f in focuses): eligible.append(pair_id)
    output_dir.mkdir(parents=True, exist_ok=True); trials = []
    for pair_id in sorted(eligible):
        readings = sorted(pairs[pair_id], key=lambda c: c["reading"])
        _plain_ps, plain_tokens = pipeline.g2p(readings[0]["target"]); rendered = []
        for index, reading in enumerate(readings):
            competing = readings[1-index]["gold_ir"]["focus_span"]
            _ps, tokens = pipeline.g2p(annotate_competing_focus(reading["target"], competing))
            validate_phoneme_contrast(plain_tokens, tokens, reading["gold_ir"]["focus_span"], competing)
            rendered.append((reading, tokens))
        for voice in VOICES:
            outputs = []
            for reading, tokens in rendered:
                result = list(pipeline.generate_from_tokens(tokens, voice=voice, speed=1.0))
                if len(result) != 1 or result[0].audio is None or not result[0].tokens: raise RuntimeError("unexpected Kokoro output")
                audio = samples(result[0].audio); path = output_dir/"audio"/voice/f"{reading['case_id']}.wav"
                path.parent.mkdir(parents=True, exist_ok=True); sf.write(path, np.asarray(audio,dtype=np.int16),24000,subtype="PCM_16")
                outputs.append({"audio":audio,"tokens":result[0].tokens,"path":str(path.relative_to(output_dir)),"sha256":digest(path.read_bytes())})
            metrics=[]
            for i, reading in enumerate(readings):
                focus=reading["gold_ir"]["focus_span"]
                metrics.append(word_metrics(outputs[i]["audio"],token_window(outputs[i]["tokens"],focus),
                    outputs[1-i]["audio"],token_window(outputs[1-i]["tokens"],focus)))
            trials.append({"trial_id":digest(f"{pair_id}:{voice}")[:24],"pair_id":pair_id,"voice":voice,
                "case_ids":[r["case_id"] for r in readings],"contexts":[r["context"] for r in readings],
                "target":readings[0]["target"],"focus_spans":[r["gold_ir"]["focus_span"] for r in readings],
                "audio_paths":[o["path"] for o in outputs],"audio_sha256":[o["sha256"] for o in outputs],
                "word_metrics":metrics,"passed":all(m["passed"] for m in metrics)})
    counts=Counter(t["voice"] for t in trials if t["passed"])
    passed=sum(t["passed"] for t in trials); gate=passed>=5 and all(counts[v]>=2 for v in VOICES)
    report={"format":PROTOCOL["format"],"version":1,"protocol":PROTOCOL,"protocol_digest":digest(canonical(PROTOCOL)),
        "eligible_pairs":sorted(eligible),"trials":trials,"passed_trials":passed,"passed_by_voice":dict(counts),"gate_passed":gate}
    (output_dir/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(canonical({k:report[k] for k in ("protocol_digest","passed_trials","passed_by_voice","gate_passed")}))
    if not gate: raise SystemExit(2)
    return report

def main():
    p=argparse.ArgumentParser(); p.add_argument("--source-run",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args()
    execute(a.source_run.resolve(),a.output_dir.resolve())
if __name__=="__main__": main()
