import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_014"
SPEC = importlib.util.spec_from_file_location("run_ablation", EXPERIMENT / "run_ablation.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class InstructionFormAblationTest(unittest.TestCase):
    def test_protocol_is_balanced_and_valid(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        MODULE.validate_protocol(protocol)
        self.assertEqual(protocol["arms"], ["positive-only", "context-only"])
        self.assertEqual(sum(len(pair["conditions"]) for pair in protocol["pairs"]), 4)

    def test_context_only_arm_cannot_name_focus(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        condition = protocol["pairs"][0]["conditions"][0]
        condition["instructions"]["context-only"] += " Emphasize library."
        with self.assertRaisesRegex(ValueError, "must not name intended focus"):
            MODULE.validate_protocol(protocol)


if __name__ == "__main__":
    unittest.main()
