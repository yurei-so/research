#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from narrative_steering import analyze_judgments


parser = argparse.ArgumentParser()
parser.add_argument("--bundle", type=Path, required=True)
parser.add_argument("--reveal", type=Path, required=True)
parser.add_argument("--judgments", type=Path, required=True)
parser.add_argument("--output", type=Path)
args = parser.parse_args()
here = Path(__file__).resolve().parent
encoded = json.dumps(analyze_judgments(here / "frozen-protocol.json", args.bundle, args.reveal, args.judgments), indent=2, sort_keys=True) + "\n"
if args.output:
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded)
    os.chmod(temporary, 0o600)
    os.replace(temporary, output)
else:
    print(encoded, end="")
