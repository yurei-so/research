import json
from pathlib import Path

from zenith_vision import create_blind_openraster

state = Path.home() / ".local/state/zenith-vision"
dataset = state / "datasets/operator-normal-validation-v1"
manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
output = state / "blind-annotation/normal-v1"
selected = (manifest["items"][0], manifest["items"][5], manifest["items"][11])
documents = [
    create_blind_openraster(dataset / item["media"], output / f"{item['id']}.ora")
    for item in selected
]
print("\n".join(str(path) for path in documents))
