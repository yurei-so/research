from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

from .dataset import sha256_file
from .layout import DEFAULT_REGION_BOXES
from .models import BoundingBox


SPLITS = ("train", "validation", "test")


def generate_synthetic_corpus(output: Path, *, count: int = 30, seed: int = 20260824) -> Path:
    """Generate a deterministic, text-free HUD corpus and a digest-bound manifest."""
    if count < 9 or count > 10_000:
        raise ValueError("synthetic corpus count must be between 9 and 10000")
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("synthetic corpus output must be empty")
    media_dir = output / "media"
    labels_dir = output / "labels"
    media_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    labels_dir.mkdir(mode=0o700, exist_ok=True)
    items: list[dict[str, object]] = []
    for index in range(count):
        item_id = f"synthetic-{index:05d}"
        split = _split_for(index)
        rng = random.Random(f"{seed}:{item_id}")
        image, labels = _render(rng)
        media_path = media_dir / f"{item_id}.png"
        labels_path = labels_dir / f"{item_id}.json"
        image.save(media_path, format="PNG", optimize=True)
        labels_path.write_text(json.dumps({"regions": labels}, separators=(",", ":")) + "\n", encoding="utf-8")
        items.append({
            "id": item_id, "media": str(media_path.relative_to(output)),
            "sha256": sha256_file(media_path), "source_class": "synthetic",
            "license": "CC0-1.0", "consent": "not_applicable",
            "redaction_status": "not_required", "split": split,
            "labels": str(labels_path.relative_to(output)),
        })
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps({
        "format": "zenith-vision.dataset-manifest", "version": 1,
        "name": f"synthetic-hud-v1-seed-{seed}", "items": items,
    }, indent=2) + "\n", encoding="utf-8")
    return manifest


def _split_for(index: int) -> str:
    bucket = index % 10
    return "train" if bucket < 7 else "validation" if bucket < 9 else "test"


def _render(rng: random.Random) -> tuple[Image.Image, list[dict[str, object]]]:
    width, height = rng.choice(((1280, 720), (1600, 900), (1920, 1080)))
    base = tuple(rng.randint(25, 85) for _ in range(3))
    image = Image.new("RGB", (width, height), base)
    draw = ImageDraw.Draw(image)
    for _ in range(80):
        x, y = rng.randrange(width), rng.randrange(height)
        radius = rng.randint(2, max(3, width // 80))
        color = tuple(min(255, channel + rng.randint(0, 80)) for channel in base)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    labels: list[dict[str, object]] = []
    for kind, template in DEFAULT_REGION_BOXES.items():
        box = _jitter(template, rng)
        pixels = _pixels(box, width, height)
        panel = tuple(rng.randint(90, 210) for _ in range(3))
        draw.rounded_rectangle(pixels, radius=max(2, width // 300), fill=panel, outline=(230, 220, 190), width=2)
        for _ in range(rng.randint(2, 8)):
            cx = rng.randint(pixels[0], max(pixels[0], pixels[2] - 1))
            cy = rng.randint(pixels[1], max(pixels[1], pixels[3] - 1))
            size = rng.randint(2, max(3, width // 150))
            draw.rectangle((cx, cy, min(pixels[2], cx + size), min(pixels[3], cy + size)), fill=(30, 30, 30))
        labels.append({"kind": kind, "box": [box.x, box.y, box.width, box.height]})
    return image, labels


def _jitter(box: BoundingBox, rng: random.Random) -> BoundingBox:
    dx, dy = rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012)
    scale = rng.uniform(0.92, 1.04)
    width, height = box.width * scale, box.height * scale
    x = min(max(0.0, box.x + dx), 1.0 - width)
    y = min(max(0.0, box.y + dy), 1.0 - height)
    return BoundingBox(x, y, width, height)


def _pixels(box: BoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    return (round(box.x * width), round(box.y * height),
            round((box.x + box.width) * width), round((box.y + box.height) * height))
