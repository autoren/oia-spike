from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_tycho_trace_integration.py"
SPEC = importlib.util.spec_from_file_location("verify_tycho_trace_integration", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
integration = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = integration
SPEC.loader.exec_module(integration)


class TychoTraceIntegrationTests(unittest.TestCase):
    def test_manifest_pins_artifacts_and_preserves_boundaries(self) -> None:
        payload = integration.validate_manifest()
        result = integration.validate_result()
        self.assertEqual(payload["status"], "logging_integration_frozen_unexecuted")
        self.assertEqual(payload["claim_boundary"]["project_reopening_effect"], "none")
        self.assertFalse(
            payload["claim_boundary"]["broad_ontology_formation_claim_reopened"]
        )
        self.assertTrue(
            all(value == 0 for value in payload["execution_boundary"].values())
        )
        self.assertEqual(result["verdict"], "credential_free_logging_integration_pass")
        self.assertEqual(result["project_reopening_effect"], "none")

    def test_artifact_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.bin"
            artifact.write_bytes(b"expected")
            manifest = root / "manifest.json"
            payload = json.loads(integration.MANIFEST.read_text(encoding="utf-8"))
            payload["artifacts"] = {
                "artifact.bin": {
                    "sha256": integration.sha256(artifact),
                    "size": artifact.stat().st_size,
                    "role": "fixture",
                }
            }
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            integration.validate_manifest(manifest, root)
            artifact.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "size mismatch|hash mismatch"):
                integration.validate_manifest(manifest, root)


if __name__ == "__main__":
    unittest.main()
