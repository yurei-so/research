from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = {
    "contract_smoke": ROOT / "experiments" / "contract_smoke" / "run.py",
    "ui_layout_baseline": ROOT / "experiments" / "ui_layout_baseline" / "run.py",
    "synthetic_corpus_smoke": ROOT / "experiments" / "synthetic_corpus_smoke" / "run.py",
    "panel_transfer_baseline": ROOT / "experiments" / "panel_transfer_baseline" / "run.py",
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in EXPERIMENTS:
        allowed = ", ".join(sorted(EXPERIMENTS))
        print(f"usage: {Path(sys.argv[0]).name} <{allowed}>", file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT / "src"))
    runpy.run_path(str(EXPERIMENTS[sys.argv[1]]), run_name="__main__")
    return 0


raise SystemExit(main())
