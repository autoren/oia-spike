from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_historical_freeze_continuity.py"
SPEC = importlib.util.spec_from_file_location("historical_freeze_continuity", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
maintenance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = maintenance
SPEC.loader.exec_module(maintenance)


class HistoricalFreezeContinuityTests(unittest.TestCase):
    def test_all_pinned_snapshots_and_current_artifacts_verify(self) -> None:
        maintenance.verify_maintenance_record()
        self.assertEqual(
            [freeze.audit_id for freeze in maintenance.FREEZES],
            [
                "OIA-1-TRACK-A-005e",
                "OIA-1-TRACK-A-006a",
                "OIA-1-TRACK-A-006b",
                "OIA-1-TRACK-A-006c",
            ],
        )
        for freeze in maintenance.FREEZES:
            result = maintenance.verify_freeze(freeze)
            self.assertTrue(result["pass"])

    def test_only_root_index_is_exempted(self) -> None:
        self.assertEqual(maintenance.MUTABLE_INDEX_PATHS, {"README.md"})
        for freeze in maintenance.FREEZES:
            entries = maintenance.read_manifest(freeze)
            self.assertIn("README.md", entries)
            maintenance.verify_current_continuity(freeze, entries)


if __name__ == "__main__":
    unittest.main()
