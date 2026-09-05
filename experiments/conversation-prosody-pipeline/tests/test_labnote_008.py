import math
import sys
import unittest
from array import array
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).parents[1] / "experiments" / "labnote_008"
sys.path.insert(0, str(EXPERIMENT_DIR))

from run_focus_gate import digest, median_f0, rms, segment  # noqa: E402


class Labnote008Tests(unittest.TestCase):
    def test_selection_digest_is_stable(self):
        self.assertEqual(digest("labnote-008:test"),
                         "8915501f2a6e4d030ada2726a8631dc3e505e24d7ad4c4b3ca44bcb40f72fcf7")

    def test_signal_metrics_detect_energy_and_pitch(self):
        low = array("h", (round(1000 * math.sin(2 * math.pi * 120 * index / 24000))
                          for index in range(2400)))
        high = array("h", (round(2000 * math.sin(2 * math.pi * 180 * index / 24000))
                           for index in range(2400)))
        self.assertGreater(rms(high), rms(low))
        self.assertAlmostEqual(median_f0(low), 120, delta=3)
        self.assertAlmostEqual(median_f0(high), 180, delta=3)
        self.assertEqual(len(segment(low, (0.01, 0.03))), 480)


if __name__ == "__main__":
    unittest.main()
