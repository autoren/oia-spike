from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_track_a_003b_admission_v2 import load_stage_result


class TrackA003bOrchestratorV2Tests(unittest.TestCase):
    def test_loads_standard_outer_evidence_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_text(json.dumps({"stage_result": {"stage": "p0", "results": []}}))
            self.assertEqual(load_stage_result(path, "p0")["results"], [])

    def test_rejects_wrong_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            path.write_text(json.dumps({"stage_result": {"stage": "full"}}))
            with self.assertRaisesRegex(ValueError, "expected 'p0'"):
                load_stage_result(path, "p0")


if __name__ == "__main__":
    unittest.main()
