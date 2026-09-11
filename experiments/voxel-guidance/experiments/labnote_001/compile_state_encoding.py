#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from voxel_guidance import evaluate_state_encodings

parser = argparse.ArgumentParser(description="Compare state encodings on the frozen pilot")
parser.add_argument("--session-root", type=Path, required=True,
                    help="Directory containing exactly the 12 accepted pilot streams")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

sessions = []
for path in sorted(args.session_root.glob("*.ndjson")):
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if events:
        sessions.append(events)

result = evaluate_state_encodings(sessions)
args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
