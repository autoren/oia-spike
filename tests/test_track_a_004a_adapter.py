from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "baseline" / "oia-v0.2.1" / "src"))

import prepare_track_a_004a as adapter
from ontology_auditor import CandidateSystem


class TrackA004aAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(
            (ROOT / "audits" / "track-a-004a" / "ADAPTER_SOURCE_TRACES.json").read_text(
                encoding="utf-8"
            )
        )

    def test_compilation_is_reproducible_and_complete(self) -> None:
        payload, outputs, states, validation = adapter.build_adapter(self.source)
        system = CandidateSystem.from_dict(payload)
        self.assertEqual(tuple(system.machines), adapter.MACHINE_IDS)
        self.assertEqual(system.actions, adapter.ACTIONS)
        self.assertIn(adapter.BOUNDARY_OUTPUT, outputs)
        self.assertGreater(len(outputs), 1)
        self.assertEqual(validation["words_replayed_total"], 168)
        self.assertEqual(validation["transition_steps_replayed_total"], 456)
        self.assertEqual(validation["result"], "pass")
        self.assertEqual(len(states["states"]), 86)
        self.assertTrue(all(len(machine.states) == 86 for machine in system.machines.values()))

    def test_boundary_sink_cannot_separate_candidates(self) -> None:
        payload, _, _, _ = adapter.build_adapter(self.source)
        system = CandidateSystem.from_dict(payload)
        for machine in system.machines.values():
            for state in machine.states:
                if int(state[1:]) >= 21:
                    for action in adapter.ACTIONS:
                        transition = machine.step(state, action)
                        self.assertEqual(transition.output, adapter.BOUNDARY_OUTPUT)
                        self.assertEqual(transition.next_state, "S085")

    def test_prefix_inconsistency_is_rejected(self) -> None:
        source = copy.deepcopy(self.source)
        source["candidates"][0]["word_records"][4]["trace"]["steps"][0][
            "final_frame_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(ValueError, "prefix-inconsistent"):
            adapter.build_adapter(source)


if __name__ == "__main__":
    unittest.main()
