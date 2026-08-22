from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_local_qwen_action_selection.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_tycho_local_qwen_action_selection", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoLocalQwenActionSelectionTests(unittest.TestCase):
    def test_protocol_changes_only_bounded_reasoning_allowance(self) -> None:
        payload = verifier.validate_protocol()
        self.assertEqual(
            payload["sole_behavioral_relaxation"][
                "public_game_model_calls_maximum"
            ],
            {"old": 2, "new": 4},
        )
        self.assertEqual(payload["authorized_execution"]["runs"], 1)
        self.assertEqual(
            payload["authorized_execution"]["semi_private_or_private_games"], 0
        )
        self.assertTrue(payload["pass_condition"]["default_actions_are_not_successes"])

    def test_protocol_fails_closed_if_a_fifth_call_is_allowed(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["authorized_execution"]["public_game_model_calls_maximum"] = 5
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution boundary changed"):
                verifier.validate_protocol(path)

    def test_protocol_fails_closed_if_default_action_can_pass(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["pass_condition"]["default_actions_are_not_successes"] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pass condition changed"):
                verifier.validate_protocol(path)

    def test_result_attributes_only_action_to_tycho_default(self) -> None:
        payload = verifier.validate_result()
        execution = payload["execution"]
        self.assertEqual(execution["tool_steps"], 4)
        self.assertEqual(execution["model_selected_non_reset_actions"], 0)
        self.assertEqual(execution["default_reason"], "default (tool cap)")
        self.assertFalse(execution["explicit_action_selection_established"])
        self.assertEqual(
            payload["next_gate"]["status"], "requires_separate_freeze"
        )

    def test_result_fails_closed_if_default_is_recast_as_model_action(self) -> None:
        payload = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        payload["execution"]["model_selected_non_reset_actions"] = 1
        payload["execution"]["explicit_action_selection_established"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "result changed"):
                verifier.validate_result(path)


if __name__ == "__main__":
    unittest.main()
