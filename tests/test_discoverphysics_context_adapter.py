from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "integrations/discoverphysics/context_adapter.py"
SPEC = importlib.util.spec_from_file_location("discoverphysics_context_adapter", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)
CONTRACT = json.loads(
    (ROOT / "integrations/discoverphysics/CONTEXT_ADAPTER_CONTRACT.json").read_text(
        encoding="utf-8"
    )
)
NONCE = "0123456789abcdef0123456789abcdef"


def experiment(start_time: float = 0.0) -> dict:
    return {
        "p1": 1.0,
        "p2": 2.0,
        "pos2": [3.0, 0.0],
        "velocity2": [0.0, 0.5],
        "measurement_times": [0.5, 1.0, 2.0, 5.0],
        "start_time": start_time,
        "duration": 5.0,
    }


def complete_trace() -> list[dict]:
    request = experiment()
    return [
        {"sequence": 0, "round": 1, "kind": "experiment_request", "payload": request},
        {
            "sequence": 1,
            "round": 1,
            "kind": "experiment_observation",
            "payload": {
                "experiment_sequence": 0,
                "measurement_times": request["measurement_times"],
                "start_time": request["start_time"],
                "pos1": [[0.0, 0.0]],
                "pos2": [[2.9, 0.1]],
                "velocity1": [[0.0, 0.0]],
                "velocity2": [[-0.1, 0.5]],
            },
        },
        {
            "sequence": 2,
            "round": 1,
            "kind": "hypothesis_revision",
            "payload": {
                "hypothesis_id": "h1",
                "hypothesis": "The executable may require absolute episode time.",
            },
        },
        {
            "sequence": 3,
            "round": 1,
            "kind": "resource_snapshot",
            "payload": {
                "model_calls": 1,
                "elapsed_seconds": 2.0,
                "input_tokens": 100,
                "output_tokens": 50,
            },
        },
        {
            "sequence": 4,
            "round": 2,
            "kind": "artifact_submission",
            "payload": {
                "artifact_sha256": "a" * 64,
                "interface_fields": list(adapter.CANDIDATE_INPUT_FIELDS),
            },
        },
    ]


class DiscoverPhysicsContextAdapterTests(unittest.TestCase):
    def test_contract_is_context_complete_and_execution_free(self) -> None:
        validated = adapter.validate_contract(CONTRACT)
        self.assertEqual(validated["status"], "context_adapter_frozen_unexecuted")
        self.assertIn(
            "start_time", validated["artifact_interface"]["candidate_input_fields"]
        )
        self.assertTrue(
            all(value == 0 for value in validated["execution_boundary"].values())
        )

    def test_current_upstream_time_blind_signature_fails_closed(self) -> None:
        time_blind = deepcopy(CONTRACT)
        for field in ("candidate_input_fields", "evaluator_forwarded_fields"):
            time_blind["artifact_interface"][field].remove("start_time")
        with self.assertRaisesRegex(ValueError, "candidate interface changed"):
            adapter.validate_contract(time_blind)

    def test_candidate_call_preserves_start_time(self) -> None:
        call = adapter.build_candidate_call(CONTRACT, experiment(2.0), 1.0)
        self.assertEqual(tuple(call), adapter.CANDIDATE_INPUT_FIELDS)
        self.assertEqual(call["start_time"], 2.0)
        self.assertEqual(call["duration"], 1.0)

    def test_matched_pair_commitment_is_deterministic_and_non_disclosing(self) -> None:
        left = experiment(0.0)
        right = experiment(2.0)
        first = adapter.commit_matched_pair(CONTRACT, left, right, NONCE)
        second = adapter.commit_matched_pair(CONTRACT, left, right, NONCE)
        self.assertEqual(first, second)
        self.assertEqual(len(first["commitment_sha256"]), 64)
        self.assertFalse(first["pair_values_disclosed"])
        self.assertFalse(first["commitment_nonce_disclosed"])
        self.assertNotIn("left", first)
        self.assertNotIn("right", first)
        self.assertNotIn("nonce", first)

        different_nonce = adapter.commit_matched_pair(
            CONTRACT, left, right, "fedcba9876543210fedcba9876543210"
        )
        self.assertNotEqual(
            first["commitment_sha256"], different_nonce["commitment_sha256"]
        )

    def test_matched_pair_rejects_a_second_changed_field(self) -> None:
        right = experiment(2.0)
        right["p1"] = 3.0
        with self.assertRaisesRegex(ValueError, "differs in fields"):
            adapter.commit_matched_pair(CONTRACT, experiment(0.0), right, NONCE)

    def test_matched_pair_rejects_a_guessable_or_malformed_nonce(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 128 bits"):
            adapter.commit_matched_pair(
                CONTRACT, experiment(0.0), experiment(2.0), "0123"
            )

    def test_private_truth_in_learner_visible_data_fails_closed(self) -> None:
        leaked = experiment()
        leaked["true_law"] = "secret"
        with self.assertRaisesRegex(ValueError, "forbidden private fields"):
            adapter.validate_experiment(leaked)

    def test_complete_trace_preserves_context_and_order(self) -> None:
        result = adapter.validate_trace(CONTRACT, complete_trace())
        self.assertTrue(result["context_complete"])
        self.assertEqual(result["events"], 5)
        self.assertEqual(result["experiments"], 1)
        self.assertEqual(result["simulator_calls_performed_by_validation"], 0)

    def test_trace_rejects_dropped_context_and_noncontiguous_order(self) -> None:
        dropped = complete_trace()
        del dropped[1]["payload"]["start_time"]
        with self.assertRaisesRegex(ValueError, "dropped or changed start_time"):
            adapter.validate_trace(CONTRACT, dropped)

        reordered = complete_trace()
        reordered[2]["sequence"] = 7
        with self.assertRaisesRegex(ValueError, "not strictly contiguous"):
            adapter.validate_trace(CONTRACT, reordered)


if __name__ == "__main__":
    unittest.main()
