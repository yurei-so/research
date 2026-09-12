import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_015"
SPEC = importlib.util.spec_from_file_location("prepare_annotation", EXPERIMENT / "prepare_annotation.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(MODULE)
ANALYZE_SPEC = importlib.util.spec_from_file_location("analyze_annotations", EXPERIMENT / "analyze_annotations.py")
ANALYZE = importlib.util.module_from_spec(ANALYZE_SPEC); assert ANALYZE_SPEC.loader; ANALYZE_SPEC.loader.exec_module(ANALYZE)


def wav(path: Path) -> str:
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * 16_000)
    return MODULE.digest(path.read_bytes())


class EmergentAnnotationPreparationTest(unittest.TestCase):
    def test_prepares_eight_blinded_owner_only_items(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "source"; (source / "audio").mkdir(parents=True)
            trials = []
            for index in range(8):
                path = source / "audio" / f"trial-{index}.wav"; sha = wav(path)
                trials.append({"trial_id": f"trial-{index}", "pair_id": "pair",
                    "condition_id": "condition", "arm": "arm", "context": "hidden",
                    "focus": "word", "instruction_sha256": "a" * 64,
                    "target": "A fixed transcript.", "audio_path": f"audio/trial-{index}.wav",
                    "audio_sha256": sha})
            (source / "report.json").write_text(json.dumps({
                "format": "conversation-prosody.instruction-focus-ablation-run",
                "integrity_gate_passed": True, "trials": trials}))
            output = root / "private"
            result = MODULE.prepare(EXPERIMENT / "protocol.json", source, output)
            bundle = json.loads((output / "annotation-bundle.json").read_text())
            self.assertEqual(result["items"], 8); self.assertEqual(len(bundle["items"]), 8)
            self.assertNotIn("focus", bundle["items"][0])
            self.assertEqual((output / "annotation-key.json").stat().st_mode & 0o777, 0o600)

    def test_rejects_incomplete_source_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "report.json").write_text(json.dumps({
                "format": "conversation-prosody.instruction-focus-ablation-run",
                "integrity_gate_passed": False, "trials": []}))
            with self.assertRaisesRegex(ValueError, "complete passing"):
                MODULE.prepare(EXPERIMENT / "protocol.json", root, root / "out")

    def test_focus_matching_uses_complete_perceived_phrases(self):
        self.assertEqual(ANALYZE.normalized_phrases("borrowed, again"), {"borrowed", "again"})
        self.assertNotIn("borrow", ANALYZE.normalized_phrases("borrowed, again"))


if __name__ == "__main__":
    unittest.main()
