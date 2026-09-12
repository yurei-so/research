import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np


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

    def test_empty_voiced_contour_bin_does_not_create_sentinel_extreme(self):
        protocol = json.loads((PATH.parent / "protocol.json").read_text())
        audio = np.concatenate([np.sin(np.arange(8000) * 2 * np.pi * 150 / 16000) * 0.2,
                                np.zeros(8000)])
        features, _ = MODULE.clip_features(audio, 16000, protocol)
        self.assertGreater(min(features["energy_thirds_db"]), -100)
        self.assertTrue(all(value > 0 for value in features["f0_thirds_hz"]))


if __name__ == "__main__":
    unittest.main()
