from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/verify_tycho_kaggle_package.py"
SPEC = importlib.util.spec_from_file_location("verify_tycho_kaggle_package", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


class TychoKagglePackageTests(unittest.TestCase):
    def test_protocol_allows_only_bundle_build_and_portability_test(self) -> None:
        payload = verifier.validate_protocol()
        authorized = payload["authorized_post_freeze_execution"]
        self.assertEqual(authorized["runtime_bundle_builds"], 1)
        self.assertEqual(authorized["clean_container_portability_tests"], 1)
        self.assertEqual(authorized["model_loads"], 0)
        self.assertEqual(authorized["arc_actions"], 0)
        self.assertEqual(authorized["kaggle_uploads"], 0)

    def test_protocol_fails_closed_on_model_load(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["authorized_post_freeze_execution"]["model_loads"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "execution boundary changed"):
                verifier.validate_protocol(path)

    def test_protocol_requires_only_host_driver_to_remain_unresolved(self) -> None:
        payload = json.loads(verifier.PROTOCOL.read_text(encoding="utf-8"))
        payload["bundle_contract"]["allowed_unresolved_shared_libraries"].append(
            "libcublas.so.13"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bundle contract changed"):
                verifier.validate_protocol(path)

    def test_protocol_keeps_package_readiness_outside_claim(self) -> None:
        payload = verifier.validate_protocol()
        unsupported = payload["claim_boundary"]["does_not_support"]
        self.assertIn("Kaggle package readiness", unsupported)
        self.assertIn("safe Tycho run_python execution", unsupported)

    def test_result_is_runtime_only_and_package_blocked(self) -> None:
        payload = verifier.validate_result()
        self.assertEqual(
            payload["verdict"],
            "runtime_bundle_qualified_adapter_sandbox_and_throughput_unqualified",
        )
        self.assertTrue(payload["claim_boundary"]["runtime_bundle_reproducible"])
        self.assertFalse(payload["claim_boundary"]["safe_run_python"])
        self.assertFalse(payload["claim_boundary"]["package_ready"])

    def test_result_fails_closed_on_extra_unresolved_library(self) -> None:
        result = json.loads(verifier.RESULT.read_text(encoding="utf-8"))
        manifest = json.loads(verifier.FILE_MANIFEST.read_text(encoding="utf-8"))
        manifest["portability_test"]["unresolved_shared_libraries"].append(
            "libcublas.so.13"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result_path = root / "result.json"
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result["runtime_bundle"]["tracked_manifest_sha256"] = hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest()
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "portability result changed"):
                verifier.validate_result(result_path, manifest_path)


if __name__ == "__main__":
    unittest.main()
