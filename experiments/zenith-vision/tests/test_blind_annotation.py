from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from zenith_vision import BLIND_LAYER_NAMES, create_blind_openraster, extract_blind_boxes


class BlindAnnotationTests(unittest.TestCase):
    def test_creates_private_blank_layered_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, document = root / "source.png", root / "blind.ora"
            Image.new("RGB", (100, 50), "navy").save(source)
            create_blind_openraster(source, document)
            with zipfile.ZipFile(document) as archive:
                self.assertEqual(archive.read("mimetype"), b"image/openraster")
                self.assertTrue(all(f"data/{name}.png" in archive.namelist() for name in BLIND_LAYER_NAMES))

    def test_extracts_filled_rectangles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, document = root / "source.png", root / "blind.ora"
            Image.new("RGB", (100, 100), "navy").save(source)
            create_blind_openraster(source, document)
            replacement = root / "painted.ora"
            with zipfile.ZipFile(document) as original, zipfile.ZipFile(replacement, "w") as output:
                for info in original.infolist():
                    payload = original.read(info.filename)
                    if info.filename.startswith("data/") and info.filename != "data/source.png":
                        layer = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
                        ImageDraw.Draw(layer).rectangle((10, 20, 39, 59), fill=(255, 0, 0, 255))
                        stream = io.BytesIO(); layer.save(stream, format="PNG"); payload = stream.getvalue()
                    output.writestr(info, payload)
            boxes = extract_blind_boxes(replacement)
            self.assertEqual(boxes["objectives"].x, 0.10)
            self.assertEqual(boxes["objectives"].height, 0.40)

    def test_applies_krita_cropped_layer_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, document = root / "source.png", root / "blind.ora"
            Image.new("RGB", (100, 100), "navy").save(source)
            create_blind_openraster(source, document)
            rewritten = root / "krita.ora"
            with zipfile.ZipFile(document) as original, zipfile.ZipFile(rewritten, "w") as output:
                stack = original.read("stack.xml").replace(b'name="objectives"', b'name="objectives" x="70" y="20"')
                for info in original.infolist():
                    payload = stack if info.filename == "stack.xml" else original.read(info.filename)
                    if info.filename == "data/objectives.png":
                        layer = Image.new("RGBA", (20, 30), (255, 0, 0, 255))
                        stream = io.BytesIO(); layer.save(stream, format="PNG"); payload = stream.getvalue()
                    elif info.filename.startswith("data/") and info.filename != "data/source.png":
                        layer = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
                        stream = io.BytesIO(); layer.save(stream, format="PNG"); payload = stream.getvalue()
                    output.writestr(info, payload)
            box = extract_blind_boxes(rewritten)["objectives"]
            self.assertEqual((box.x, box.y, box.width, box.height), (0.7, 0.2, 0.2, 0.3))

    def test_rejects_empty_layers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, document = root / "source.png", root / "blind.ora"
            Image.new("RGB", (100, 100), "navy").save(source)
            create_blind_openraster(source, document)
            with self.assertRaisesRegex(ValueError, "empty"):
                extract_blind_boxes(document)


if __name__ == "__main__":
    unittest.main()
