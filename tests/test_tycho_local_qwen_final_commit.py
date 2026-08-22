from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_local_qwen_final_commit.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_tycho_local_qwen_final_commit", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoLocalQwenFinalCommitTests(unittest.TestCase):
    def test_protocol_reserves_exactly_one_commit_only_call(self) -> None:
        payload = verifier.validate_protocol()
        self.assertEqual(
            payload["single_change"]["public_game_model_calls_maximum"],
            {"old": 4, "new": 5},
        )
        self.assertEqual(
            payload["authorized_execution"][
                "public_game_tool_steps_per_turn_maximum"
            ],
            4,
        )
        self.assertEqual(
            payload["pass_condition"]["required_tool_trace"],
            {"tool": "take_action", "committed": True, "final_commit": True},
        )

    def test_protocol_fails_closed_if_tool_allowance_also_increases(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["authorized_execution"][
            "public_game_tool_steps_per_turn_maximum"
        ] = 5
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution boundary changed"):
                verifier.validate_protocol(path)

    def test_protocol_fails_closed_if_default_action_can_pass(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["pass_condition"]["tycho_default_actions_are_not_successes"] = False
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pass condition changed"):
                verifier.validate_protocol(path)


if __name__ == "__main__":
    unittest.main()
