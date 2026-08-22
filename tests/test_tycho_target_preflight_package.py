from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_target_preflight_package.py"
SPEC = importlib.util.spec_from_file_location("verify_tycho_target_preflight_package", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoTargetPreflightPackageTests(unittest.TestCase):
    def test_protocol_is_package_only(self) -> None:
        payload = verifier.validate_protocol()
        execution = payload["authorized_post_freeze_execution"]
        self.assertEqual(execution["bundle_builds"], 1)
        self.assertEqual(execution["target_notebook_runs"], 0)
        self.assertEqual(execution["kaggle_uploads"], 0)
        self.assertEqual(execution["model_loads"], 0)

    def test_manifest_pins_x86_binary_and_offline_sources(self) -> None:
        payload = verifier.validate_manifest()
        entries = {entry["path"]: entry for entry in payload["entries"]}
        self.assertEqual(entries["bin/sandlock"]["mode"], 0o755)
        self.assertIn("source/tycho-f68912a.tar.gz", entries)

    def test_result_keeps_target_execution_pending(self) -> None:
        payload = verifier.validate_result()
        claims = payload["claim_boundary"]
        self.assertFalse(claims["target_kernel_support"])
        self.assertFalse(claims["x86_64_sandlock_execution"])
        self.assertFalse(claims["kaggle_upload_or_notebook_run"])

    def test_tampered_manifest_fails_closed(self) -> None:
        payload = json.loads(verifier.MANIFEST.read_text(encoding="utf-8"))
        payload["entries"][1]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical entry hash changed"):
                verifier.validate_manifest(path)


if __name__ == "__main__":
    unittest.main()
