from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_track_a_005a_prediction_diagnostic as diagnostic


class TrackA005aPredictionDiagnosticTests(unittest.TestCase):
    def test_identical_frames_have_zero_error(self) -> None:
        rows = ["0" * 64 for _ in range(64)]
        result = diagnostic.descriptive_metrics(
            p0_rows=rows,
            predicted_rows=rows,
            actual_rows=rows,
        )
        self.assertEqual(result["pixel_mismatch_count"], 0)
        self.assertEqual(result["delta_union_count"], 0)
        self.assertEqual(result["delta_jaccard_fraction"], {"numerator": 0, "denominator": 0})

    def test_delta_metrics_are_exact_counts(self) -> None:
        p0 = ["0" * 64 for _ in range(64)]
        predicted = list(p0)
        actual = list(p0)
        predicted[0] = "12" + "0" * 62
        actual[0] = "13" + "0" * 62
        result = diagnostic.descriptive_metrics(
            p0_rows=p0,
            predicted_rows=predicted,
            actual_rows=actual,
        )
        self.assertEqual(result["pixel_mismatch_count"], 1)
        self.assertEqual(result["predicted_delta_pixel_count"], 2)
        self.assertEqual(result["actual_delta_pixel_count"], 2)
        self.assertEqual(result["delta_intersection_count"], 2)
        self.assertEqual(result["delta_union_count"], 2)


if __name__ == "__main__":
    unittest.main()
