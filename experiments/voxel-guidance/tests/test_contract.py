from __future__ import annotations

import unittest

from voxel_guidance import ContractError, compile_session_features, validate_session, validate_session_set


def event(sequence: int, kind: str, payload: dict, second: int) -> dict:
    return {
        "format": "voxel-guidance.event", "version": 1,
        "session_id": "session-test-001", "sequence": sequence,
        "observed_at": f"2026-09-07T12:00:{second:02d}Z",
        "instance_id": "Voxel Guidance Lab", "task_id": "rehearsal-001",
        "kind": kind, "payload": payload,
    }


class ContractTests(unittest.TestCase):
    def fixture(self) -> list[dict]:
        return [
            event(0, "session_start", {"protocol_id": "rehearsal-v1"}, 0),
            event(1, "position_sample", {"x": 0, "y": 64, "z": 0, "dimension": "overworld"}, 5),
            event(2, "marker", {"marker": "plan_started"}, 10),
            event(3, "inventory_delta", {"category": "resource", "delta": 6}, 15),
            event(4, "block_action", {"action": "placed", "category": "building", "count": 2}, 20),
            event(5, "position_sample", {"x": 16, "y": 64, "z": 0, "dimension": "overworld"}, 25),
            event(6, "marker", {"marker": "setback"}, 30),
            event(7, "marker", {"marker": "recovered"}, 35),
            event(8, "session_end", {"reason": "completed"}, 40),
        ]

    def test_validates_and_compiles_interpretable_features(self) -> None:
        events = self.fixture()
        self.assertEqual(validate_session(events), events)
        result = compile_session_features(events)
        self.assertEqual(result["metrics"]["exploration_cells"], 2)
        self.assertEqual(result["metrics"]["route_directness"], 1.0)
        self.assertEqual(result["metrics"]["resource_selectivity"], 1.0)
        self.assertEqual(result["metrics"]["setback_recovery_rate"], 1.0)
        self.assertEqual(result["metrics"]["first_marker_latency_fraction"], 0.25)

    def test_rejects_unowned_instance_and_unknown_fields(self) -> None:
        events = self.fixture()
        events[1]["instance_id"] = "Personal world"
        with self.assertRaisesRegex(ContractError, "toolkit-owned"):
            validate_session(events)
        events = self.fixture()
        events[1]["payload"]["player_name"] = "not allowed"
        with self.assertRaisesRegex(ContractError, "payload shape"):
            validate_session(events)

    def test_rejects_sequence_gaps_and_cross_session_data(self) -> None:
        events = self.fixture()
        events[3]["sequence"] = 30
        with self.assertRaisesRegex(ContractError, "contiguous"):
            validate_session(events)
        events = self.fixture()
        events[3]["session_id"] = "another-session"
        with self.assertRaisesRegex(ContractError, "cross-session"):
            validate_session(events)

    def test_rejects_missing_boundaries_and_time_reversal(self) -> None:
        events = self.fixture()[1:]
        for sequence, item in enumerate(events):
            item["sequence"] = sequence
        with self.assertRaisesRegex(ContractError, "boundaries"):
            validate_session(events)
        events = self.fixture()
        events[4]["observed_at"] = "2026-09-07T12:00:01Z"
        with self.assertRaisesRegex(ContractError, "backwards"):
            validate_session(events)

    def test_rejects_nonfinite_coordinates(self) -> None:
        events = self.fixture()
        events[1]["payload"]["x"] = float("nan")
        with self.assertRaisesRegex(ContractError, "finite"):
            validate_session(events)

    def test_missing_marker_is_not_encoded_as_maximal_latency(self) -> None:
        events = [item for item in self.fixture() if item["kind"] != "marker"]
        for sequence, item in enumerate(events):
            item["sequence"] = sequence
        self.assertIsNone(compile_session_features(events)["metrics"]["first_marker_latency_fraction"])

    def test_session_set_requires_distinct_session_ids(self) -> None:
        first = self.fixture()
        second = self.fixture()
        self.assertEqual(len(validate_session_set([first])), 1)
        with self.assertRaisesRegex(ContractError, "duplicate session_id"):
            validate_session_set([first, second])


if __name__ == "__main__":
    unittest.main()
