#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from narrative_steering import analyze_judgments


parser = argparse.ArgumentParser()
parser.add_argument("--bundle", type=Path, required=True)
parser.add_argument("--reveal", type=Path, required=True)
parser.add_argument("--judgments", type=Path, required=True)
args = parser.parse_args()
here = Path(__file__).resolve().parent
print(json.dumps(analyze_judgments(here / "frozen-protocol.json", args.bundle, args.reveal, args.judgments), indent=2, sort_keys=True))
