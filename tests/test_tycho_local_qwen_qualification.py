from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_local_qwen_qualification.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_tycho_local_qwen_qualification", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoLocalQwenQualificationTests(unittest.TestCase):
    def test_protocol_preserves_opened_engineering_boundary(self) -> None:
        payload = verifier.validate_protocol()
        self.assertEqual(payload["status"], "frozen_unexecuted")
        self.assertEqual(
            payload["authorized_execution"]["public_game_model_calls_maximum"], 2
        )
        self.assertEqual(
            payload["authorized_execution"]["semi_private_or_private_games"], 0
        )
        self.assertEqual(payload["claim_boundary"]["project_reopening_effect"], "none")

    def test_maintenance_changes_only_the_local_dollar_guard(self) -> None:
        payload = verifier.validate_maintenance()
        self.assertEqual(payload["single_correction"]["new_value"], "0")
        self.assertEqual(
            payload["unchanged_boundaries"]["public_game_model_calls_maximum"], 2
        )
        self.assertTrue(
            all(
                attempt["model_calls"] == 0
                and attempt["resets"] == 0
                and attempt["committed_actions"] == 0
                for attempt in payload["premaintenance_attempts"]
            )
        )

    def test_protocol_fails_closed_if_model_bytes_change(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["model"]["model_file"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "model boundary changed"):
                verifier.validate_protocol(path)

    def test_protocol_fails_closed_if_a_third_game_call_is_allowed(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["authorized_execution"]["public_game_model_calls_maximum"] = 3
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution boundary changed"):
                verifier.validate_protocol(path)

    def test_maintenance_fails_closed_if_behavior_preceded_correction(self) -> None:
        payload = json.loads(verifier.MAINTENANCE.read_text(encoding="utf-8"))
        payload["premaintenance_attempts"][1]["model_calls"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "followed qualification behavior"):
                verifier.validate_maintenance(path)

    def test_result_preserves_default_action_attribution(self) -> None:
        payload = verifier.validate_result()
        result = payload["public_harness_result"]
        self.assertEqual(result["model_calls"], 2)
        self.assertEqual(result["tool_steps"], 2)
        self.assertEqual(result["environment_action_sequence"], ["ACTION1"])
        self.assertEqual(result["default_reason"], "default (tool cap)")
        self.assertFalse(result["action_selection_by_model_established"])
        self.assertEqual(payload["next_gate"]["status"], "not_authorized_by_this_result")

    def test_result_fails_closed_if_default_action_is_recast_as_model_choice(self) -> None:
        payload = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        payload["public_harness_result"][
            "action_selection_by_model_established"
        ] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "action attribution changed"):
                verifier.validate_result(path)

    def test_result_fails_closed_if_private_evaluation_is_added(self) -> None:
        payload = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        payload["public_harness_result"]["semi_private_or_private_games"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "zero boundary"):
                verifier.validate_result(path)


if __name__ == "__main__":
    unittest.main()
