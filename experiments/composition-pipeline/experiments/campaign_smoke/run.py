from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from composition_pipeline.campaign import Trial, load_campaign, run_campaign


ROOT = Path(__file__).resolve().parent


def execute(trial: Trial) -> dict[str, Any]:
    return {
        "metrics": {"valid": True, "parameter_count": len(trial.parameters)},
        "receipt": {"repetition": trial.repetition},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run_campaign(load_campaign(ROOT / "manifest.json"), args.state_dir, execute)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
