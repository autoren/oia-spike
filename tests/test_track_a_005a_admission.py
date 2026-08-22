from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_track_a_005a_admission as prepare
import run_track_a_005a_admission_and_oia as run


def trace(candidate: str, word: tuple[str, ...]) -> dict[str, object]:
    steps = []
    for index, action in enumerate(word, start=1):
        suffix = "left" if candidate == "C0006" and action == "ACTION6" else "shared"
        steps.append(
            {
                "absorbed": False,
                "action": action,
                "final_frame_sha256": f"{index}-{action}-{suffix}",
                "status": "RUNNING",
            }
        )
    return {
        "status": "pass",
        "error_category": None,
        "p0": {"matches_frame": True},
        "word": list(word),
        "steps": steps,
    }


def full_result() -> dict[str, object]:
    records = []
    for candidate in run.EXPECTED_CANDIDATES:
        word_records = []
        for word in run.frozen_words():
            observed = trace(candidate, word)
            repetitions = [
                {"seed": seed, "repetition": repetition, "trace": observed}
                for seed in run.SEEDS
                for repetition in run.REPETITIONS
            ]
            word_records.append(
                {
                    "word": list(word),
                    "deterministic": True,
                    "trace_sha256": [run.sha256_bytes(run.canonical_bytes(observed))],
                    "repetitions": repetitions,
                }
            )
        records.append(
            {
                "candidate_id": candidate,
                "candidate_sha256": candidate.lower(),
                "all_words_pass": True,
                "deterministic": True,
                "word_records": word_records,
            }
        )
    return {
        "stage": "full",
        "seeds": list(run.SEEDS),
        "repetitions_per_seed": 2,
        "word_count": 14,
        "records": records,
        "admitted_candidates": list(run.EXPECTED_CANDIDATES),
    }


class TrackA005aAdmissionTests(unittest.TestCase):
    def test_frozen_binary_words_are_complete_and_ordered(self) -> None:
        words = run.frozen_words()
        self.assertEqual(len(words), 14)
        self.assertEqual(words[:2], [("ACTION6",), ("ACTION7",)])
        self.assertEqual(words[-1], ("ACTION7", "ACTION7", "ACTION7"))

    def test_hardened_scan_accepts_fixture_and_rejects_file_loader(self) -> None:
        source = (
            ROOT / "tests" / "fixtures" / "track-a-005a" / "synthetic_candidate" / "candidate.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(prepare.hardened_static_scan(source)["result"], "pass")
        with self.assertRaisesRegex(ValueError, "attributes"):
            prepare.hardened_static_scan(source.replace("np.asarray", "np.load"))

    def test_adapter_is_complete_and_uses_observable_fields_only(self) -> None:
        payload, validation = run.build_adapter(full_result())
        self.assertEqual([machine["name"] for machine in payload["machines"]], ["M0001", "M0002"])
        self.assertEqual(validation["observation_fields"], ["final_frame_sha256", "status"])
        self.assertEqual(run.independent_separator(full_result()), ("ACTION6",))
        for machine in payload["machines"]:
            self.assertEqual(len(machine["transitions"]), 16)
            self.assertTrue(all(set(edges) == set(run.ACTIONS) for edges in machine["transitions"].values()))


if __name__ == "__main__":
    unittest.main()
