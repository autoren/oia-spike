"""Deterministic structural scaling evidence plus local console timings.

The checksummed artifact ``scaling_probe_results.json`` contains only
platform-independent structural outputs. Wall-clock measurements are printed to
stdout with a ``TIMING_LOCAL`` prefix and are deliberately never written to a
manifested file. Rerunning this script therefore leaves the deterministic JSON
byte-for-byte unchanged when the algorithms and interpreter semantics agree.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, TypeVar

from ontology_auditor import (
    CandidateSystem,
    MealyMachine,
    Transition,
    shortest_pairwise_separator,
    synthesize_adaptive_policy,
    synthesize_preset_sequence,
)

T = TypeVar("T")


def isolate_one_family(candidate_count: int) -> CandidateSystem:
    actions = tuple(f"test_{i}" for i in range(candidate_count - 1))
    machines = []
    for candidate in range(candidate_count):
        outputs = {
            action: ("yes" if candidate == action_index else "no")
            for action_index, action in enumerate(actions)
        }
        machines.append(
            MealyMachine(
                name=f"H{candidate}",
                initial_state="s",
                transitions={
                    "s": {
                        action: Transition(output, "s")
                        for action, output in outputs.items()
                    }
                },
            )
        )
    return CandidateSystem(machines)


def delayed_pair(length: int) -> CandidateSystem:
    actions = ("advance", "inspect")
    machines = []
    for name, terminal_output in (("left", "red"), ("right", "blue")):
        transitions = {}
        for index in range(length + 1):
            state = f"s{index}"
            next_index = min(index + 1, length)
            transitions[state] = {
                "advance": Transition("ok", f"s{next_index}"),
                "inspect": Transition(
                    terminal_output if index == length else "neutral",
                    state,
                ),
            }
        machines.append(MealyMachine(name, "s0", transitions))
    return CandidateSystem(machines)


def timed(callable_: Callable[[], T]) -> tuple[T, float]:
    start = time.perf_counter()
    result = callable_()
    return result, time.perf_counter() - start


def collect() -> tuple[dict[str, object], list[dict[str, object]]]:
    structural_rows: list[dict[str, object]] = []
    timing_rows: list[dict[str, object]] = []

    for count in (4, 6, 8, 10, 12):
        system = isolate_one_family(count)
        adaptive, adaptive_seconds = timed(
            lambda: synthesize_adaptive_policy(system, max_beliefs=1_000_000)
        )
        preset, preset_seconds = timed(
            lambda: synthesize_preset_sequence(system, max_partitions=1_000_000)
        )
        structural_rows.append(
            {
                "family": "isolate_one",
                "candidate_count": count,
                "adaptive_status": adaptive.status,
                "adaptive_exact": adaptive.exact,
                "adaptive_depth_claim": adaptive.depth_claim,
                "adaptive_worst_case_steps": adaptive.worst_case_steps,
                "reachable_beliefs": adaptive.reachable_beliefs,
                "preset_status": preset.status,
                "preset_exact": preset.exact,
                "preset_length": len(preset.sequence or ()),
                "explored_partitions": preset.explored_partitions,
            }
        )
        timing_rows.append(
            {
                "family": "isolate_one",
                "candidate_count": count,
                "adaptive_seconds": adaptive_seconds,
                "preset_seconds": preset_seconds,
            }
        )

    for length in (4, 8, 16, 32, 64, 128):
        system = delayed_pair(length)
        separation, seconds = timed(
            lambda: shortest_pairwise_separator(system, "left", "right")
        )
        structural_rows.append(
            {
                "family": "delayed_pair",
                "delay": length,
                "distinguishable": separation.distinguishable,
                "separator_length": len(separation.sequence or ()),
            }
        )
        timing_rows.append(
            {
                "family": "delayed_pair",
                "delay": length,
                "pair_seconds": seconds,
            }
        )

    evidence: dict[str, object] = {
        "schema_version": 2,
        "evidence_class": "deterministic_structural_scaling_probe",
        "timing_policy": (
            "wall-clock values are console-only local diagnostics and are not "
            "included in this checksummed artifact"
        ),
        "rows": structural_rows,
    }
    return evidence, timing_rows


def main() -> None:
    evidence, timing_rows = collect()
    output = Path(__file__).with_name("scaling_probe_results.json")
    output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for row in evidence["rows"]:
        print("STRUCTURAL", json.dumps(row, sort_keys=True))
    for row in timing_rows:
        print("TIMING_LOCAL", json.dumps(row, sort_keys=True))
    print(f"wrote deterministic structural evidence {output}")


if __name__ == "__main__":
    main()
