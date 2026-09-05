from __future__ import annotations

import json


print(json.dumps({
    "format": "composition-pipeline.experiment-result",
    "version": 1,
    "experiment": "contract_smoke",
    "status": "ok",
}, separators=(",", ":")))
