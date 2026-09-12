import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_017"
SPEC = importlib.util.spec_from_file_location("run_candidate_pool", EXPERIMENT / "run_candidate_pool.py")
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(MODULE)


class CandidatePoolTest(unittest.TestCase):
    def test_frozen_protocol_has_twelve_unique_trials(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        MODULE.validate_protocol(protocol)
        trials = {(utterance["id"], recipe["id"]) for utterance in protocol["utterances"]
                  for recipe in protocol["reading_recipes"]}
        self.assertEqual(len(trials), 12)

    def test_rejects_wrong_pool_shape(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        protocol["utterances"].pop()
        with self.assertRaisesRegex(ValueError, "three recipes across four utterances"):
            MODULE.validate_protocol(protocol)

    def test_annotation_protocol_blinds_recipe_identity(self):
        protocol = json.loads((EXPERIMENT / "annotation_protocol.json").read_text())
        self.assertEqual(protocol["expected_items"], 12)
        self.assertIn("recipe_id", protocol["blind_fields"])


if __name__ == "__main__":
    unittest.main()
