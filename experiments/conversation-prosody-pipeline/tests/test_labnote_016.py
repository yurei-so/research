import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
PATH = ROOT / "experiments" / "labnote_016" / "extract_fingerprints.py"
SPEC = importlib.util.spec_from_file_location("extract_fingerprints", PATH)
MODULE = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(MODULE)


class AcousticFingerprintTest(unittest.TestCase):
    def test_standardize_centers_values(self):
        values = MODULE.standardize([1.0, 2.0, 3.0])
        self.assertAlmostEqual(sum(values), 0.0)

    def test_exact_cluster_test_detects_perfect_separation(self):
        result = MODULE.cluster_test([[0.0], [0.1], [0.2], [10.0], [10.1], [10.2]],
                                     [False, False, False, True, True, True])
        self.assertGreater(result["statistic"], 0)
        self.assertEqual(result["permutations"], 20)
        self.assertLessEqual(result["exact_p_value"], 0.10)

    def test_normalize_removes_punctuation(self):
        self.assertEqual(MODULE.normalize("Again!"), "again")


if __name__ == "__main__":
    unittest.main()
