import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_012"
SPEC = importlib.util.spec_from_file_location("validate_references", EXPERIMENT / "validate_references.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_wav(path: Path, seconds: float = 1.1) -> None:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * int(16_000 * seconds))


class ReferenceFocusValidationTest(unittest.TestCase):
    def test_validates_four_private_references_and_writes_owner_only_manifest(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pair in protocol["pairs"]:
                for condition in pair["conditions"]:
                    write_wav(root / condition["reference_file"])
            output = root / "private" / "manifest.json"
            manifest = MODULE.validate(EXPERIMENT / "protocol.json", root, output)
            self.assertEqual(len(manifest["references"]), 4)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_rejects_missing_or_non_pcm_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing reference"):
                MODULE.validate(EXPERIMENT / "protocol.json", Path(directory), Path(directory) / "out.json")


if __name__ == "__main__":
    unittest.main()
