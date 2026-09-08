#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from narrative_steering import calibrate_scorer, compile_fingerprints


def write_private(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600); os.replace(temporary, path)


parser = argparse.ArgumentParser()
parser.add_argument("--reveal", type=Path, required=True)
parser.add_argument("--human", type=Path, required=True)
parser.add_argument("--automated", type=Path)
parser.add_argument("--fingerprints", type=Path, required=True)
parser.add_argument("--calibration", type=Path)
args = parser.parse_args()
protocol = Path(__file__).resolve().parent / "frozen-protocol.json"
write_private(args.fingerprints.resolve(), compile_fingerprints(protocol, args.reveal, args.human))
if args.automated or args.calibration:
    if not args.automated or not args.calibration:
        raise SystemExit("--automated and --calibration must be supplied together")
    write_private(args.calibration.resolve(), calibrate_scorer(protocol, args.reveal, args.human, args.automated))
