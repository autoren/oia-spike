from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_track_a_006a_controlled_open_world.py"
SPEC = importlib.util.spec_from_file_location("track_a_006a_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class TrackA006aControlledOpenWorldTests(unittest.TestCase):
    def test_benchmark_and_fixture_seed_namespaces_are_disjoint(self) -> None:
        self.assertNotEqual(runner.BENCHMARK_MASTER_SEED, runner.FIXTURE_MASTER_SEED)
        benchmark = runner.derived_seed(runner.BENCHMARK_MASTER_SEED, "candidate", 0, 0, 0)
        fixture = runner.derived_seed(runner.FIXTURE_MASTER_SEED, "candidate", 0, 0, 0)
        self.assertNotEqual(benchmark, fixture)

    def test_delayed_generator_hides_identity_at_the_first_observation(self) -> None:
        machine = runner.random_delayed_machine(
            "H",
            123,
            state_count=3,
            action_count=3,
            output_count=3,
        )
        self.assertEqual(
            {machine.step(machine.initial_state, action).output for action in machine.actions},
            {"o0"},
        )

    def test_fixture_is_deterministic_and_in_family_oia_is_sound(self) -> None:
        first = runner.collect(runner.fixture_config())
        second = runner.collect(runner.fixture_config())
        self.assertEqual(runner.pretty_bytes(first[0]), runner.pretty_bytes(second[0]))
        self.assertEqual(runner.pretty_bytes(first[1]), runner.pretty_bytes(second[1]))
        self.assertEqual(runner.pretty_bytes(first[2]), runner.pretty_bytes(second[2]))
        in_family_oia = [
            item
            for item in first[2]
            if item["policy"] == "oia_adaptive" and item["target_kind"] == "in_family"
        ]
        self.assertTrue(in_family_oia)
        self.assertEqual(
            {item["status"] for item in in_family_oia},
            {"correct_candidate_identification"},
        )

    def test_fixture_evidence_zip_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            runner.write_outcome(first, runner.fixture_config())
            runner.write_outcome(second, runner.fixture_config())
            self.assertEqual(
                (first / "CONTROLLED_OPEN_WORLD_EVIDENCE.zip").read_bytes(),
                (second / "CONTROLLED_OPEN_WORLD_EVIDENCE.zip").read_bytes(),
            )
            self.assertEqual(
                (first / "CONTROLLED_OPEN_WORLD_RESULT.json").read_bytes(),
                (second / "CONTROLLED_OPEN_WORLD_RESULT.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
