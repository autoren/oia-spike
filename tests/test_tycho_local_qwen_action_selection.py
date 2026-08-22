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


if __name__ == "__main__":
    unittest.main()
