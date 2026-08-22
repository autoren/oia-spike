from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_discoverphysics_context_adapter.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_discoverphysics_context_adapter", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class DiscoverPhysicsContextAdapterVerifierTests(unittest.TestCase):
    def test_manifest_binds_adapter_and_preserves_boundaries(self) -> None:
        payload = verifier.validate_manifest()
        self.assertEqual(payload["status"], "context_adapter_frozen_unexecuted")
        self.assertTrue(all(value == 0 for value in payload["execution_boundary"].values()))
        self.assertEqual(payload["claim_boundary"]["project_reopening_effect"], "none")

    def test_manifest_fails_closed_if_an_artifact_hash_changes(self) -> None:
        payload = json.loads(verifier.MANIFEST.read_text(encoding="utf-8"))
        first = next(iter(payload["artifacts"].values()))
        first["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                verifier.validate_manifest(path, ROOT)

    def test_manifest_fails_closed_if_execution_is_authorized(self) -> None:
        payload = json.loads(verifier.MANIFEST.read_text(encoding="utf-8"))
        payload["execution_boundary"]["model_calls_authorized"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "crossed execution boundary"):
                verifier.validate_manifest(path, ROOT)


if __name__ == "__main__":
    unittest.main()
