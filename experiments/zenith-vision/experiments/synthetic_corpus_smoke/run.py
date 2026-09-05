from __future__ import annotations

import json
import tempfile
from pathlib import Path

from zenith_vision import DatasetManifest, generate_synthetic_corpus

with tempfile.TemporaryDirectory(prefix="zenith-vision-synthetic-") as directory:
    manifest = DatasetManifest.load(generate_synthetic_corpus(Path(directory), count=20))
    counts = manifest.split_counts()
    status = "ok" if counts == {"train": 14, "validation": 4, "test": 2} else "failed"
    print(json.dumps({
        "format": "zenith-vision.experiment-result", "version": 1,
        "experiment": "synthetic_corpus_smoke", "status": status,
        "metrics": {"items": len(manifest.items), "splits": counts, "digest_validated": len(manifest.items)},
    }, separators=(",", ":")))
    raise SystemExit(0 if status == "ok" else 1)
