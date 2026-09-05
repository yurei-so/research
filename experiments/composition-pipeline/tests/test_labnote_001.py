import json
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from composition_pipeline.editor import apply_edit_document


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "experiments/labnote_001/run.py"
SPEC = importlib.util.spec_from_file_location("labnote_001_run", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LABNOTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LABNOTE)


class Labnote001Test(unittest.TestCase):
    def test_frozen_protocol_and_corpus_are_bounded(self) -> None:
        protocol = json.loads(
            (ROOT / "experiments/labnote_001/frozen-protocol.json").read_text()
        )
        corpus = json.loads((ROOT / "experiments/labnote_001/corpus.json").read_text())
        self.assertEqual(protocol["experiment_id"], "labnote_001")
        self.assertEqual(len(corpus["cases"]), 6)
        self.assertEqual(len({case["id"] for case in corpus["cases"]}), 6)

    def test_protocol_example_is_applicable(self) -> None:
        result, edits = apply_edit_document({"operations": [
            {"op": "append", "text": "A draft is absolutely always correct."},
            {"op": "replace", "old": "absolutely always", "new": "usually"},
            {"op": "finalize"},
        ]})
        self.assertEqual(result, "A draft is usually correct.")
        self.assertEqual(edits, 1)

    def test_edit_arm_records_success_without_exposing_raw_protocol(self) -> None:
        generated = {
            "text": json.dumps({"operations": [
                {"op": "append", "text": "rough text"},
                {"op": "replace", "old": "rough", "new": "polished"},
                {"op": "finalize"},
            ]}),
            "eval_count": 20,
            "prompt_eval_count": 40,
            "elapsed_seconds": 0.5,
        }
        with patch.object(LABNOTE, "generate", return_value=generated):
            result = LABNOTE.run_edit_arm(
                task="write", model="test", base_url="http://127.0.0.1", constrained=True
            )
        self.assertTrue(result["semantic_apply_success"])
        self.assertEqual(result["final_text"], "polished text")
        self.assertEqual(result["edit_operation_count"], 1)
        self.assertNotIn("operations", result)
