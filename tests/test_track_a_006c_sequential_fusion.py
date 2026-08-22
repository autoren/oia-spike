from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_track_a_006c_sequential_fusion.py"
SPEC = importlib.util.spec_from_file_location("track_a_006c_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class TrackA006cSequentialFusionTests(unittest.TestCase):
    def test_fixture_and_benchmark_namespaces_are_disjoint(self) -> None:
        self.assertNotEqual(runner.BENCHMARK_MASTER_SEED, runner.FIXTURE_MASTER_SEED)

    def test_closed_detection_is_preserved_without_reset(self) -> None:
        closed = {
            "action_trace": ["a0"],
            "identified_candidate": None,
            "output_trace": ["novel"],
            "status": "outside_model",
            "steps": 1,
        }
        reject = {
            "action_trace": ["a1"],
            "identified_candidate": "H0",
            "output_trace": ["o0"],
            "status": "false_candidate_identification",
            "steps": 1,
        }
        fused = runner.fuse("outside", "OUTSIDE", closed, reject)
        self.assertEqual(fused["status"], "outside_detected_closed")
        self.assertEqual(fused["reset_count"], 0)
        self.assertEqual(fused["steps"], 1)
        self.assertNotIn("__reset__", fused["action_trace"])

    def test_disagreement_rejects_after_explicit_reset(self) -> None:
        closed = {
            "action_trace": ["a0"],
            "identified_candidate": "H0",
            "output_trace": ["o0"],
            "status": "false_candidate_identification",
            "steps": 1,
        }
        reject = {
            "action_trace": ["a1", "a2"],
            "identified_candidate": "H1",
            "output_trace": ["o0", "o1"],
            "status": "false_candidate_identification",
            "steps": 2,
        }
        fused = runner.fuse("outside", "OUTSIDE", closed, reject)
        self.assertEqual(fused["status"], "outside_detected_disagreement")
        self.assertEqual(fused["reset_count"], 1)
        self.assertEqual(fused["steps"], 3)
        self.assertEqual(fused["action_trace"], ["a0", "__reset__", "a1", "a2"])

    def test_fixture_is_deterministic_sound_and_preserves_closed_detection(self) -> None:
        first = runner.collect(runner.fixture_config())
        second = runner.collect(runner.fixture_config())
        self.assertEqual(runner.pretty_bytes(first[0]), runner.pretty_bytes(second[0]))
        self.assertEqual(runner.pretty_bytes(first[1]), runner.pretty_bytes(second[1]))
        self.assertEqual(runner.pretty_bytes(first[2]), runner.pretty_bytes(second[2]))
        fused_in = [
            item
            for item in first[2]
            if item["policy"] == "sequential_fusion" and item["target_kind"] == "in_family"
        ]
        self.assertEqual(len(fused_in), 12)
        self.assertEqual(
            {item["status"] for item in fused_in},
            {"correct_candidate_identification"},
        )
        by_target: dict[tuple[str, str], dict[str, dict[str, object]]] = {}
        for item in first[2]:
            key = (item["case_id"], item["target_id"])
            by_target.setdefault(key, {})[item["policy"]] = item
        for policies in by_target.values():
            if policies["closed_identity_native"]["status"] == "outside_model":
                self.assertEqual(
                    policies["sequential_fusion"]["status"],
                    "outside_detected_closed",
                )

    def test_fixture_package_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            runner.write_outcome(first, runner.fixture_config())
            runner.write_outcome(second, runner.fixture_config())
            self.assertEqual(
                (first / "SEQUENTIAL_FUSION_EVIDENCE.zip").read_bytes(),
                (second / "SEQUENTIAL_FUSION_EVIDENCE.zip").read_bytes(),
            )
            self.assertEqual(
                (first / "SEQUENTIAL_FUSION_RESULT.json").read_bytes(),
                (second / "SEQUENTIAL_FUSION_RESULT.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
