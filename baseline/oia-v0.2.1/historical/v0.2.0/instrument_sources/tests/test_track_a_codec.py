from __future__ import annotations

import json
import unittest
from pathlib import Path

from ontology_auditor import CandidateSystem, initial_behavioral_classes


class TrackACodecRegressionTests(unittest.TestCase):
    """Regression checks discovered by the first opened external adapter."""

    def test_codec_partition_converges_after_stable_split(self) -> None:
        root = Path(__file__).resolve().parents[1]
        payload = json.loads(
            (
                root
                / "external"
                / "cpython_codecs"
                / "audit_001"
                / "audit_input.opaque.json"
            ).read_text(encoding="utf-8")
        )
        system = CandidateSystem.from_dict(payload)
        classes = initial_behavioral_classes(system)

        # The prior global-signature implementation reached five singleton
        # initial classes but then kept renumbering stable blocks forever.
        self.assertEqual(len(classes), 5)
        self.assertEqual(
            sorted(model for group in classes for model in group),
            sorted(system.machines),
        )
        self.assertTrue(all(len(group) == 1 for group in classes))


if __name__ == "__main__":
    unittest.main()
