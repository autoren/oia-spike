from __future__ import annotations

import ast
from enum import Enum
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


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

    def test_synthetic_worker_and_evidence_path_end_to_end(self) -> None:
        class GameAction(Enum):
            RESET = 0
            ACTION6 = 6
            ACTION7 = 7

        class GameState(Enum):
            NOT_FINISHED = "NOT_FINISHED"

        class ActionInput:
            def __init__(self, id: GameAction, data: dict[str, int]) -> None:
                self.id = id
                self.data = data

        class FakeArray:
            shape = (64, 64)

            def __init__(self, value: int) -> None:
                self.value = value

            def tolist(self) -> list[list[int]]:
                return [[self.value] * 64 for _ in range(64)]

        arcengine = types.ModuleType("arcengine")
        arcengine.ActionInput = ActionInput
        arcengine.GameAction = GameAction
        arcengine.GameState = GameState
        numpy = types.ModuleType("numpy")
        numpy.uint8 = object()
        numpy.full = lambda _shape, value, dtype=None: FakeArray(value)
        source = """from typing import Any
import numpy as np
from arcengine import GameAction, GameState

class cqrtilsbtt:
    def __init__(self, value: int, action_input: Any) -> None:
        self.frame = [np.full((64, 64), value, dtype=np.uint8)]
        self.state = GameState.NOT_FINISHED
        self.available_actions = [6, 7]

class Su15:
    def __init__(self) -> None:
        pass

    def perform_action(self, action_input: Any, raw: bool = False) -> cqrtilsbtt:
        values = {GameAction.RESET: 0, GameAction.ACTION6: 1, GameAction.ACTION7: 2}
        return cqrtilsbtt(values[action_input.id], action_input)
"""

        def frame_hash(value: int) -> str:
            return runner.sha256_bytes(runner.frame_to_text(FakeArray(value)).encode("ascii"))

        protocol = {
            "exact_reproduction": {
                "p0_final_frame_sha256": frame_hash(0),
                "p1_final_frame_sha256": frame_hash(1),
            },
            "candidate_predictions": {
                "SYNTHETIC_TRUE": {"final_frame_sha256": frame_hash(2), "status": "RUNNING"},
                "SYNTHETIC_OTHER": {"final_frame_sha256": frame_hash(3), "status": "RUNNING"},
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_path = Path(temporary) / "synthetic_source.py"
            source_path.write_text(source, encoding="utf-8")
            with (
                mock.patch.dict(sys.modules, {"arcengine": arcengine, "numpy": numpy}),
                mock.patch.object(runner, "read_protocol", return_value=protocol),
                mock.patch.object(runner, "preflight", return_value={"pass": True}),
                mock.patch.object(runner, "disable_network"),
            ):
                runs = [
                    runner.worker(source_path, source_path, x, y, repetition)
                    for x, y in ((4, 59), (48, 15))
                    for repetition in (1, 2)
                ]
            self.assertEqual(
                runner.result_verdict(runs, protocol),
                ("local_action7_matches_one_candidate", ["SYNTHETIC_TRUE"]),
            )
            first = Path(temporary) / "first.zip"
            second = Path(temporary) / "second.zip"
            runner.write_evidence(first, runs)
            runner.write_evidence(second, runs)
            self.assertEqual(first.read_bytes(), second.read_bytes())

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
