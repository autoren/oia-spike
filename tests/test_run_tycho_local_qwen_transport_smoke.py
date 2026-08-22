from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/run_tycho_local_qwen_transport_smoke.py"
SPEC = importlib.util.spec_from_file_location(
    "run_tycho_local_qwen_transport_smoke", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class TychoLocalQwenTransportSmokeTests(unittest.TestCase):
    def test_frozen_environment_is_accepted(self) -> None:
        self.assertEqual(runner.validate_environment(dict(runner.EXPECTED)), runner.EXPECTED)

    def test_remote_endpoint_is_rejected(self) -> None:
        environ = dict(runner.EXPECTED)
        environ["LLM_BASE_URL"] = "https://example.invalid/v1"
        with self.assertRaisesRegex(ValueError, "setting changed"):
            runner.validate_environment(environ)

    def test_registered_credential_is_rejected(self) -> None:
        environ = dict(runner.EXPECTED)
        environ["OPENAI_API_KEY"] = "not-admissible"
        with self.assertRaisesRegex(ValueError, "credential entered"):
            runner.validate_environment(environ)


if __name__ == "__main__":
    unittest.main()
