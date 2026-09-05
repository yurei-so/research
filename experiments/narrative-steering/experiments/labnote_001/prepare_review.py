#!/usr/bin/env python3
import argparse
from pathlib import Path

from narrative_steering import prepare_review


parser = argparse.ArgumentParser()
parser.add_argument("--generations", type=Path, required=True)
parser.add_argument("--bundle", type=Path, required=True)
parser.add_argument("--reveal", type=Path, required=True)
args = parser.parse_args()
here = Path(__file__).resolve().parent
prepare_review(here / "frozen-protocol.json", here / "corpus.json", args.generations, args.bundle, args.reveal)
print("Prepared 48-item blinded review bundle.")
