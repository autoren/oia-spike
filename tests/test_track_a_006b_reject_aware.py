from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_track_a_006b_reject_aware.py"
SPEC = importlib.util.spec_from_file_location("track_a_006b_runner", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class TrackA006bRejectAwareTests(unittest.TestCase):
    def test_benchmark_and_fixture_namespaces_are_disjoint(self) -> None:
        self.assertNotEqual(runner.BENCHMARK_MASTER_SEED, runner.FIXTURE_MASTER_SEED)
        self.assertNotEqual(
            runner.parent.derived_seed(runner.BENCHMARK_MASTER_SEED, "base", 0, 0, 0),
            runner.parent.derived_seed(runner.FIXTURE_MASTER_SEED, "base", 0, 0, 0),
        )

    def test_reject_terminal_requires_base_exclusion_or_clean_singleton(self) -> None:
        World = runner.parent.World
        self.assertTrue(runner.reject_aware_terminal((World("S0", "s0"),)))
        self.assertTrue(runner.reject_aware_terminal((World("H0", "s0"),)))
        self.assertFalse(
            runner.reject_aware_terminal(
                (World("H0", "s0"), World("S0", "s0"))
            )
        )
        self.assertFalse(
            runner.reject_aware_terminal(
                (World("H0", "s0"), World("H1", "s0"))
            )
        )

    def test_fixture_is_deterministic_and_native_policies_are_sound(self) -> None:
        first = runner.collect(runner.fixture_config())
        second = runner.collect(runner.fixture_config())
        self.assertEqual(runner.pretty_bytes(first[0]), runner.pretty_bytes(second[0]))
        self.assertEqual(runner.pretty_bytes(first[1]), runner.pretty_bytes(second[1]))
        self.assertEqual(runner.pretty_bytes(first[2]), runner.pretty_bytes(second[2]))
        for policy in ("closed_identity_native", "reject_aware_native"):
            in_family = [
                item
                for item in first[2]
                if item["policy"] == policy and item["target_kind"] == "in_family"
            ]
            self.assertEqual(len(in_family), 12)
            self.assertEqual(
                {item["status"] for item in in_family},
                {"correct_candidate_identification"},
            )

    def test_fixture_is_globally_distinct_and_policy_witnesses_verify(self) -> None:
        config = runner.fixture_config()
        for case_index in range(config["case_count"]):
            base, augmented, outside, closed, reject, _manifest = runner.generate_case(
                config, case_index
            )
            self.assertTrue(
                runner.globally_distinct([*augmented.machines.values(), outside])
            )
            self.assertEqual(
                runner.verify_policy_witness(base, closed.policy),
                closed.worst_case_steps,
            )
            self.assertEqual(
                runner.verify_policy_witness(
                    augmented, reject.policy, runner.reject_aware_terminal
                ),
                reject.worst_case_steps,
            )

    def test_fixture_evidence_zip_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            runner.write_outcome(first, runner.fixture_config())
            runner.write_outcome(second, runner.fixture_config())
            self.assertEqual(
                (first / "REJECT_AWARE_EVIDENCE.zip").read_bytes(),
                (second / "REJECT_AWARE_EVIDENCE.zip").read_bytes(),
            )
            self.assertEqual(
                (first / "REJECT_AWARE_RESULT.json").read_bytes(),
                (second / "REJECT_AWARE_RESULT.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
