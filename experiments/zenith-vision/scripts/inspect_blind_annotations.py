import json
from pathlib import Path

from zenith_vision import extract_blind_boxes

root = Path.home() / ".local/state/zenith-vision/blind-annotation/normal-v1"
results = {}
for document in sorted(root.glob("*.ora")):
    boxes = extract_blind_boxes(document)
    results[document.stem] = {
        name: [box.x, box.y, box.width, box.height] for name, box in boxes.items()
    }
print(json.dumps(results, separators=(",", ":")))
