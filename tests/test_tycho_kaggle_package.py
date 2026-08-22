from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
