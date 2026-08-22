from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_sandlock.py"
SPEC = importlib.util.spec_from_file_location("verify_tycho_sandlock", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoSandlockTests(unittest.TestCase):
    def test_frozen_artifacts_and_patch_scope(self) -> None:
        freeze = verifier.validate_freeze()
        self.assertFalse(freeze["patch"]["logging_or_trace_semantics_changed"])
        self.assertFalse(freeze["patch"]["prompt_or_agent_policy_changed"])
        self.assertFalse(freeze["patch"]["auto_runtime_selection_changed_to_sandlock"])

    def test_live_probe_has_positive_controls_and_negative_capabilities(self) -> None:
        payload = verifier.validate_live()
        self.assertEqual(payload["unsandboxed_control"], {"tcp": True, "udp": True})
        denied = [item for item in payload["attempts"] if not item["allowed"]]
        self.assertEqual(len(denied), 7)

    def test_result_keeps_target_and_package_unqualified(self) -> None:
        payload = verifier.validate_result()
        claims = payload["claim_boundary"]
        self.assertFalse(claims["target_evaluator_kernel_support"])
        self.assertFalse(claims["package_ready"])
        self.assertFalse(claims["oia_discovery_or_transfer"])

    def test_tampered_live_capability_fails_closed(self) -> None:
        payload = json.loads(verifier.LIVE.read_text(encoding="utf-8"))
        payload["attempts"][2]["allowed"] = True
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "capability result changed"):
                verifier.validate_live(path)


if __name__ == "__main__":
    unittest.main()
