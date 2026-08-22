from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_track_a_005e_local_outcome.py"
SPEC = importlib.util.spec_from_file_location("track_a_005e_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class TrackA005eLocalOutcomeTests(unittest.TestCase):
    def test_source_structure_is_static_and_does_not_execute(self) -> None:
        source = b"from typing import Any\nimport numpy as np\nfrom arcengine import ARCBaseGame\nclass cqrtilsbtt: pass\nclass Su15:\n    def __init__(self): pass\n"
        structure = runner.source_structure(source)
        self.assertEqual(structure["imports"], ["arcengine", "numpy", "typing"])
        self.assertEqual(structure["top_level_classes"], ["cqrtilsbtt", "Su15"])
        self.assertEqual(structure["su15_constructor_positional_arguments"], ["self"])
        self.assertIsInstance(ast.parse(source), ast.Module)

    def test_constructor_seed_matches_official_wrapper_behavior(self) -> None:
        class WithoutSeed:
            def __init__(self) -> None:
                pass

        class WithSeed:
            def __init__(self, seed: int = 0) -> None:
                self.seed = seed

        self.assertEqual(runner.constructor_kwargs(WithoutSeed, 0), {})
        self.assertEqual(runner.constructor_kwargs(WithSeed, 0), {"seed": 0})

    def test_verdict_matches_exactly_one_candidate(self) -> None:
        protocol = {
            "candidate_predictions": {
                "R1": {"final_frame_sha256": "a" * 64, "status": "RUNNING"},
                "R2": {"final_frame_sha256": "b" * 64, "status": "RUNNING"},
            }
        }
        runs = [
            {"stopped_after": "ACTION7", "action7": {"final_frame_sha256": "a" * 64, "status": "RUNNING"}},
            {"stopped_after": "ACTION7", "action7": {"final_frame_sha256": "a" * 64, "status": "RUNNING"}},
        ]
        self.assertEqual(runner.result_verdict(runs, protocol), ("local_action7_matches_one_candidate", ["R1"]))

    def test_p1_mismatch_stops_before_outcome_classification(self) -> None:
        runs = [
            {"stopped_after": "ACTION6"},
            {"stopped_after": "ACTION7", "action7": {"final_frame_sha256": "a" * 64, "status": "RUNNING"}},
        ]
        self.assertEqual(runner.result_verdict(runs, {"candidate_predictions": {}}), ("local_p1_reproduction_blocker", []))

    def test_manifest_source_hash_constant_is_sha256(self) -> None:
        self.assertEqual(len(runner.EXPECTED_SOURCE_SHA256), hashlib.sha256().digest_size * 2)


if __name__ == "__main__":
    unittest.main()
