from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_discoverphysics_context_adapter_result.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_discoverphysics_context_adapter_result", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class DiscoverPhysicsContextAdapterResultTests(unittest.TestCase):
    def test_result_preserves_freeze_order_and_execution_boundary(self) -> None:
        payload = verifier.validate_result()
        self.assertEqual(
            payload["verdict"],
            "credential_free_context_adapter_qualification_pass",
        )
        self.assertTrue(
            all(value == 0 for value in payload["execution_accounting"].values())
        )
        self.assertIsNone(payload["next_empirical_gate"])
        self.assertEqual(payload["project_reopening_effect"], "none")

    def test_result_fails_closed_if_failed_attempt_is_erased(self) -> None:
        payload = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        payload["attempts"] = payload["attempts"][1:]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "attempt accounting changed"):
                verifier.validate_result(path, ROOT)

    def test_result_fails_closed_if_an_episode_is_added(self) -> None:
        payload = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        payload["execution_accounting"]["interactive_discovery_episodes"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "crossed execution boundary"):
                verifier.validate_result(path, ROOT)


if __name__ == "__main__":
    unittest.main()
