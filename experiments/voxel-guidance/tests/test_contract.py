from __future__ import annotations

import unittest
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from voxel_guidance import (ContractError, compile_pilot, compile_session_features,
                            validate_protocol, validate_session, validate_session_set)


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
        self.assertEqual(result, compile_session_features(events))
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

    def test_accepts_precise_modern_end_reasons(self) -> None:
        for reason in ("explicit_stop", "disconnected"):
            events = self.fixture()
            events[-1]["payload"]["reason"] = reason
            self.assertEqual(validate_session(events)[-1]["payload"]["reason"], reason)

    def test_accepts_remaining_bounded_telemetry_vocabulary(self) -> None:
        events = [
            event(0, "session_start", {"protocol_id": "rehearsal-v1"}, 0),
            event(1, "inventory_delta", {"category": "tool", "delta": 1}, 1),
            event(2, "block_action", {"action": "broken", "category": "resource", "count": 1}, 2),
            event(3, "damage", {"amount": 20.0, "source_category": "other"}, 3),
            event(4, "death", {}, 3),
            event(5, "respawn", {}, 4),
            event(6, "session_end", {"reason": "explicit_stop"}, 5),
        ]
        checked = validate_session(events)
        self.assertEqual([item["kind"] for item in checked[1:-1]],
                         ["inventory_delta", "block_action", "damage", "death", "respawn"])

    def test_excludes_post_death_inventory_churn_until_recovery_marker(self) -> None:
        events = [
            event(0, "session_start", {"protocol_id": "rehearsal-v1"}, 0),
            event(1, "inventory_delta", {"category": "resource", "delta": 2}, 1),
            event(2, "death", {}, 2),
            event(3, "inventory_delta", {"category": "resource", "delta": -10}, 3),
            event(4, "respawn", {}, 4),
            event(5, "inventory_delta", {"category": "resource", "delta": 10}, 5),
            event(6, "marker", {"marker": "recovered"}, 6),
            event(7, "inventory_delta", {"category": "building", "delta": 2}, 7),
            event(8, "session_end", {"reason": "explicit_stop"}, 8),
        ]
        result = compile_session_features(events)
        self.assertEqual(result["quality"]["inventory_events_excluded_during_recovery"], 2)
        self.assertEqual(result["metrics"]["resource_selectivity"], 0.5)


ROOT = Path(__file__).parents[1]


def pilot_event(session_id: str, task_id: str, sequence: int, kind: str,
                payload: dict, second: int) -> dict:
    observed = datetime(2026, 9, 8, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "format": "voxel-guidance.event", "version": 1,
        "session_id": session_id, "sequence": sequence,
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "instance_id": "Voxel Guidance Lab", "task_id": task_id,
        "kind": kind, "payload": payload,
    }


def pilot_session(task_id: str, task: str) -> list[dict]:
    rows = [
        ("session_start", {"protocol_id": "pilot-v1"}, 0),
        ("marker", {"marker": "plan_started"}, 10),
        ("position_sample", {"x": 0, "y": 64, "z": 0, "dimension": "overworld"}, 20),
        ("position_sample", {"x": 64, "y": 64, "z": 32, "dimension": "overworld"}, 100),
    ]
    if task == "acquire":
        rows += [("inventory_delta", {"category": "resource", "delta": 4}, 150),
                 ("position_sample", {"x": 2, "y": 64, "z": 1, "dimension": "overworld"}, 300)]
    elif task == "construct":
        rows += [("block_action", {"action": "placed", "category": "building", "count": 8}, 150),
                 ("inventory_delta", {"category": "building", "delta": -8}, 151)]
    elif task == "recover":
        rows += [("marker", {"marker": "setback"}, 120), ("damage", {"amount": 20, "source_category": "other"}, 121),
                 ("death", {}, 121), ("respawn", {}, 130), ("marker", {"marker": "recovered"}, 200)]
    rows += [("marker", {"marker": "task_complete"}, 470),
             ("session_end", {"reason": "explicit_stop"}, 480)]
    return [pilot_event("session-" + task_id, task_id, index, kind, payload, second)
            for index, (kind, payload, second) in enumerate(rows)]


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads((ROOT / "experiments/labnote_001/frozen-protocol.json").read_text())
        cls.manifest = json.loads((ROOT / "experiments/labnote_001/modpack-manifest.json").read_text())

    def sessions(self) -> list[list[dict]]:
        return [pilot_session(f"vg-{block['id']}-{task}", task)
                for block in self.protocol["blocks"] for task in block["order"]]

    def test_frozen_protocol_and_manifest_are_bound(self) -> None:
        result = validate_protocol(self.protocol, self.manifest)
        self.assertEqual(len(result["protocol_digest"]), 64)
        self.assertEqual(len(result["manifest_digest"]), 64)

    def test_compiles_only_aggregate_deterministic_fingerprint(self) -> None:
        sessions = self.sessions()
        first = compile_pilot(self.protocol, self.manifest, sessions)
        self.assertEqual(first, compile_pilot(self.protocol, self.manifest, sessions))
        self.assertEqual(first["session_count"], 12)
        self.assertEqual(set(first["coordinates"]), set(self.protocol["fingerprint_coordinates"]))
        self.assertNotIn("sessions", first)
        self.assertNotIn("blocks", first)

    def test_rejects_incomplete_matrix_and_nonexplicit_stop(self) -> None:
        sessions = self.sessions()
        with self.assertRaisesRegex(ContractError, "matrix is incomplete"):
            compile_pilot(self.protocol, self.manifest, sessions[:-1])
        sessions = self.sessions()
        sessions[0][-1]["payload"]["reason"] = "disconnected"
        with self.assertRaisesRegex(ContractError, "explicit stop"):
            compile_pilot(self.protocol, self.manifest, sessions)

    def test_rejects_manifest_drift(self) -> None:
        manifest = json.loads(json.dumps(self.manifest))
        next(mod for mod in manifest["mods"] if mod["file"] == "voxel-guidance-bridge-0.1.0.jar")["sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "bridge digest mismatch"):
            validate_protocol(self.protocol, manifest)


if __name__ == "__main__":
    unittest.main()
