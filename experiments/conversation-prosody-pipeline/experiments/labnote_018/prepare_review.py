#!/usr/bin/env python3
"""Prepare a blinded, whole-conversation review page for Prosody 018."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import shutil


def prepare(run_dir: Path, review_dir: Path) -> dict[str, str]:
    report = json.loads((run_dir / "report.json").read_text())
    if (report.get("format") != "conversation-prosody.two-speaker-context-ab-run"
            or not report.get("integrity_gate_passed")):
        raise ValueError("review requires a complete, mechanically valid Prosody 018 run")
    conversations = report.get("conversations", [])
    if {row.get("arm") for row in conversations} != {"isolated", "conversation-aware"}:
        raise ValueError("review requires both frozen arms")
    seed = int(report["protocol_sha256"][:16], 16)
    shuffled = list(conversations)
    random.Random(seed).shuffle(shuffled)
    review_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    audio_dir = review_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    key: dict[str, str] = {}
    cards = []
    for index, row in enumerate(shuffled):
        item_id = chr(ord("A") + index)
        destination = audio_dir / f"conversation-{item_id.casefold()}.wav"
        shutil.copy2(run_dir / row["audio_path"], destination)
        key[item_id] = row["arm"]
        cards.append(f'''<article><span class="item">CONVERSATION {item_id}</span>
<audio controls preload="metadata" src="audio/{destination.name}"></audio>
<fieldset><legend>What survived the full scene?</legend>
<label><input type="checkbox"> Individual voices sound natural</label>
<label><input type="checkbox"> Speakers sound like they are reacting to each other</label>
<label><input type="checkbox"> Turn timing feels conversational</label>
<label><input type="checkbox"> I would call the complete exchange convincing</label></fieldset>
<label class="notes">Observation<textarea aria-label="Observation for conversation {item_id}"></textarea></label></article>''')
    key_path = review_dir / "review-key.json"
    key_path.write_text(json.dumps({"format": "conversation-prosody.two-speaker-context-ab-key",
                                    "version": 1, "items": key}, indent=2, sort_keys=True) + "\n")
    key_path.chmod(0o600)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Prosody 018 blind review</title>
<style>:root{{color-scheme:dark;font-family:system-ui,sans-serif;background:#090a10;color:#e3e4ee}}body{{max-width:900px;margin:auto;padding:42px 22px 80px}}h1{{margin-bottom:.3rem;font-size:clamp(2rem,7vw,3.4rem)}}.intro{{max-width:68ch;color:#a9abba;line-height:1.55}}main{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:32px}}article{{padding:20px;border:1px solid #303241;background:#11131b}}.item{{color:#a98aff;font:12px ui-monospace,monospace;letter-spacing:.1em}}audio{{width:100%;margin:20px 0}}fieldset{{display:grid;gap:12px;padding:0;border:0}}legend{{margin-bottom:12px;font-weight:650}}label{{color:#c7c8d2}}input{{margin-right:8px}}.notes{{display:grid;gap:7px;margin-top:18px}}textarea{{min-height:90px;padding:9px;border:1px solid #303241;color:#e3e4ee;background:#090a10;resize:vertical}}@media(max-width:680px){{main{{grid-template-columns:1fr}}}}</style></head><body>
<h1>Two-speaker blind review</h1><p class="intro">Listen to each complete scene without trying to identify its recipe. Judge what you actually hear. The script, two voices, seeds, generation settings, and authored silence gaps are matched.</p>
<p class="intro">The boxes stay in this browser only. When you are satisfied, tell Codex which boxes survived for A and B plus any observations.</p><main>{''.join(cards)}</main></body></html>'''
    (review_dir / "index.html").write_text(page)
    return key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    args = parser.parse_args()
    key = prepare(args.run_dir.resolve(), args.review_dir.resolve())
    print(json.dumps({"items": len(key), "blinded": True}, sort_keys=True))


if __name__ == "__main__":
    main()
