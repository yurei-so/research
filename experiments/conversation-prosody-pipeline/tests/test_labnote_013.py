import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
EXPERIMENT = ROOT / "experiments" / "labnote_013"
SPEC = importlib.util.spec_from_file_location("run_instruction_focus", EXPERIMENT / "run_instruction_focus.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class InstructionFocusProtocolTest(unittest.TestCase):
    def test_frozen_protocol_is_valid_and_balanced(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        MODULE.validate_protocol(protocol)
        self.assertEqual(protocol["speaker"], "Aiden")
        self.assertEqual(sum(len(pair["conditions"]) for pair in protocol["pairs"]), 4)
        self.assertEqual(len(protocol["seeds"]), 2)

    def test_rejects_unpaired_competing_focus(self):
        protocol = json.loads((EXPERIMENT / "protocol.json").read_text())
        protocol["pairs"][0]["conditions"][0]["competing_focus"] = "Tuesday"
        with self.assertRaisesRegex(ValueError, "competing focus"):
            MODULE.validate_protocol(protocol)


if __name__ == "__main__":
    unittest.main()
