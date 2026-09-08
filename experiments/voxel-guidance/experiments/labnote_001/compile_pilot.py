#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from voxel_guidance import compile_pilot
from voxel_guidance.pilot import load_json


parser = argparse.ArgumentParser(description="Compile the frozen Voxel Guidance pilot")
parser.add_argument("--session-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

here = Path(__file__).resolve().parent
protocol = load_json(here / "frozen-protocol.json")
manifest = load_json(here / "modpack-manifest.json")
expected = {f"vg-{block['id']}-{task}" for block in protocol["blocks"] for task in block["order"]}
sessions = []
for path in sorted(args.session_root.glob("*.ndjson")):
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if events and events[0].get("task_id") in expected:
        sessions.append(events)

result = compile_pilot(protocol, manifest, sessions)
args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")

