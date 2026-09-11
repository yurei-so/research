import unittest
import mujoco
from yurei_mujoco_lab import (ARENA_XML, POLICIES, arena_digest, calibration_report,
                              causal_windows, simulate_policy, simulate_sequence)

class ApparatusTests(unittest.TestCase):
    def test_arena_compiles(self):
        model=mujoco.MjModel.from_xml_string(ARENA_XML)
        self.assertEqual(model.nu,2)

    def test_replays_are_deterministic_and_finite(self):
        for name in POLICIES:
            first=simulate_policy(name,seconds=2,sample_hz=10)
            second=simulate_policy(name,seconds=2,sample_hz=10)
            self.assertEqual(first,second)
            self.assertEqual(first["arena_digest"],arena_digest())
            self.assertGreater(len(first["samples"]),15)

    def test_policies_diverge(self):
        ends={name:(round(r["samples"][-1]["x"],3),round(r["samples"][-1]["y"],3))
              for name in POLICIES for r in [simulate_policy(name,seconds=4)]}
        self.assertGreater(len(set(ends.values())),2)

    def test_sequence_is_deterministic_and_marks_phases(self):
        phases=["explore","acquire","recover"]
        first=simulate_sequence(phases,seconds_per_phase=2,sample_hz=10)
        self.assertEqual(first,simulate_sequence(phases,seconds_per_phase=2,sample_hz=10))
        self.assertEqual(set(row["phase"] for row in first["samples"]),set(phases))

    def test_features_do_not_depend_on_fixture_annotations(self):
        replay=simulate_policy("explore",seconds=5,sample_hz=10)
        original=causal_windows(replay,window_seconds=2)[0]["features"]
        for row in replay["samples"]:
            row.update(phase="recover",phase_index=99,phase_elapsed=99,waypoint=99)
        changed=causal_windows(replay,window_seconds=2)[0]["features"]
        self.assertTrue((original == changed).all())

    def test_calibration_is_bounded_and_reports_abstention(self):
        report=calibration_report()
        self.assertEqual(len(report["threshold_sweep"]),4)
        selected=next(row for row in report["threshold_sweep"]
                      if row["threshold"] == report["recommended_threshold"])
        self.assertEqual(selected["false_guidance_events"],0)
        for result in report["threshold_sweep"]:
            self.assertLessEqual(result["guidance_per_minute"],10)
            self.assertGreaterEqual(result["coverage"],0)
            self.assertLessEqual(result["coverage"],1)

if __name__ == "__main__": unittest.main()
