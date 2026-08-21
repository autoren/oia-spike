from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


class HashSeedReproducibilityTests(unittest.TestCase):
    def test_audit_002_report_and_policy_are_cross_process_deterministic(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "research" / "hash_seed_reproducibility.py"
        spec = importlib.util.spec_from_file_location("hash_seed_reproducibility", script)
        if spec is None or spec.loader is None:
            self.fail("could not load hash-seed regression module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.run_regression(module.DEFAULT_SEEDS)
        module.validate_result(result)
        self.assertEqual(
            result["unique_report_sha256"],
            [module.EXPECTED_REPORT_SHA256],
        )
        self.assertEqual(
            result["unique_policy_sha256"],
            [module.EXPECTED_POLICY_SHA256],
        )
        self.assertEqual(
            result["unique_tie_branch_actions"],
            [module.EXPECTED_TIE_ACTION],
        )


if __name__ == "__main__":
    unittest.main()
