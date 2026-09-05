from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image

from .models import BoundingBox


BLIND_LAYER_NAMES = ("objectives", "skill_bar", "minimap")


def create_blind_openraster(source: Path, destination: Path) -> Path:
    """Create a private layered ORA without exposing any seeded geometry."""
    with Image.open(source) as opened:
        background = opened.convert("RGBA")
    width, height = background.size
    transparent = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    stack = ET.Element("image", {"version": "0.0.1", "w": str(width), "h": str(height),
                                  "name": destination.stem})
    layers = ET.SubElement(stack, "stack", {"name": "root"})
    for name in BLIND_LAYER_NAMES:
        ET.SubElement(layers, "layer", {"name": name, "src": f"data/{name}.png"})
    ET.SubElement(layers, "layer", {
        "name": "source_locked", "src": "data/source.png", "edit-locked": "true",
    })
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            archive.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
            archive.writestr("stack.xml", ET.tostring(stack, encoding="utf-8", xml_declaration=True))
            archive.writestr("data/source.png", _png_bytes(background))
            archive.writestr("mergedimage.png", _png_bytes(background))
            thumbnail = background.copy()
            thumbnail.thumbnail((256, 256), Image.Resampling.LANCZOS)
            archive.writestr("Thumbnails/thumbnail.png", _png_bytes(thumbnail))
            for name in BLIND_LAYER_NAMES:
                archive.writestr(f"data/{name}.png", _png_bytes(transparent))
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def extract_blind_boxes(document: Path, *, minimum_fill: float = 0.90) -> dict[str, BoundingBox]:
    """Extract one nearly solid rectangular alpha mask from each named layer."""
    boxes: dict[str, BoundingBox] = {}
    with zipfile.ZipFile(document) as archive:
        root = ET.fromstring(archive.read("stack.xml"))
        canvas_width, canvas_height = int(root.get("w", "0")), int(root.get("h", "0"))
        if canvas_width <= 0 or canvas_height <= 0:
            raise ValueError("blind annotation document has invalid canvas dimensions")
        named = {layer.get("name"): layer for layer in root.iter("layer")}
        for name in BLIND_LAYER_NAMES:
            element = named.get(name)
            if element is None or not element.get("src"):
                raise ValueError(f"missing blind annotation layer: {name}")
            with Image.open(io.BytesIO(archive.read(element.get("src", "")))) as layer:
                alpha = layer.convert("RGBA").getchannel("A")
                bounds = alpha.getbbox()
                if bounds is None:
                    raise ValueError(f"empty blind annotation layer: {name}")
                x1, y1, x2, y2 = bounds
                occupied = sum(1 for value in alpha.crop(bounds).tobytes() if value > 0)
                area = (x2 - x1) * (y2 - y1)
                if area == 0 or occupied / area < minimum_fill:
                    raise ValueError(f"blind annotation layer is not a filled rectangle: {name}")
                offset_x, offset_y = int(element.get("x", "0")), int(element.get("y", "0"))
                absolute_x1, absolute_y1 = offset_x + x1, offset_y + y1
                normalized_x, normalized_y = absolute_x1 / canvas_width, absolute_y1 / canvas_height
                boxes[name] = BoundingBox(
                    normalized_x, normalized_y,
                    min((x2 - x1) / canvas_width, 1.0 - normalized_x),
                    min((y2 - y1) / canvas_height, 1.0 - normalized_y),
                )
    return boxes


def _png_bytes(image: Image.Image) -> bytes:
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()
