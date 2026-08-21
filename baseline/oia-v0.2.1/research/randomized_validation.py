"""Deterministic randomized differential checks for the v0.2 exact core.

This is implementation validation, not a scientific benchmark. The generated
instances are intentionally tiny enough that independent exhaustive oracles can
check shortest sequences and adaptive depths without heuristic cutoffs.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

from ontology_auditor import (
    CandidateSystem,
    MealyMachine,
    Transition,
    initial_behavioral_classes,
    shortest_pairwise_separator,
    synthesize_adaptive_policy,
    synthesize_preset_sequence,
)
from ontology_auditor.model import Belief


SEED = 20260821
STATIC_CASES = 200
DYNAMIC_PAIR_CASES = 100


@dataclass(frozen=True)
class ValidationSummary:
    static_cases: int
    dynamic_pair_cases: int
    pair_checks: int
    adaptive_checks: int
    preset_checks: int


def random_static_system(rng: random.Random) -> CandidateSystem:
    candidate_count = rng.randint(2, 5)
    actions = ("a", "b", "c")
    outputs = ("0", "1", "2")
    return CandidateSystem(
        [
            MealyMachine(
                name=f"H{candidate_index}",
                initial_state="s",
                transitions={
                    "s": {
                        action: Transition(rng.choice(outputs), "s")
                        for action in actions
                    }
                },
            )
            for candidate_index in range(candidate_count)
        ]
    )


def random_dynamic_pair(rng: random.Random) -> CandidateSystem:
    actions = ("a", "b")
    outputs = ("0", "1")
    state_count = rng.randint(1, 3)
    machines = []
    for candidate_index in range(2):
        transitions = {}
        for state_index in range(state_count):
            state = f"s{state_index}"
            transitions[state] = {
                action: Transition(
                    output=rng.choice(outputs),
                    next_state=f"s{rng.randrange(state_count)}",
                )
                for action in actions
            }
        machines.append(MealyMachine(f"H{candidate_index}", "s0", transitions))
    return CandidateSystem(machines)


def traces_differ(system: CandidateSystem, left: str, right: str, sequence: tuple[str, ...]) -> bool:
    return system.trace(left, sequence) != system.trace(right, sequence)


def brute_pair_minimum(system: CandidateSystem, left: str, right: str, max_length: int) -> tuple[str, ...] | None:
    for length in range(1, max_length + 1):
        for sequence in itertools.product(system.actions, repeat=length):
            if traces_differ(system, left, right, sequence):
                return sequence
    return None


def brute_adaptive_solvable(system: CandidateSystem, belief: Belief, depth: int, memo: dict[tuple[Belief, int], bool]) -> bool:
    if len(belief) <= 1:
        return True
    if depth == 0:
        return False
    key = (belief, depth)
    if key in memo:
        return memo[key]
    result = any(
        all(
            brute_adaptive_solvable(system, successor, depth - 1, memo)
            for successor in system.step_belief(belief, action).values()
        )
        for action in system.actions
    )
    memo[key] = result
    return result


def brute_preset_solvable(system: CandidateSystem, length: int) -> bool:
    names = sorted(system.machines)
    for sequence in itertools.product(system.actions, repeat=length):
        traces = [system.trace(name, sequence) for name in names]
        if len(traces) == len(set(traces)):
            return True
    return False


def run() -> ValidationSummary:
    rng = random.Random(SEED)
    pair_checks = 0
    adaptive_checks = 0
    preset_checks = 0

    # Static one-state candidates keep the complete belief/partition graphs
    # small, allowing exhaustive cross-checks for multi-candidate policies.
    for _ in range(STATIC_CASES):
        system = random_static_system(rng)
        classes = initial_behavioral_classes(system)
        class_by_model = {
            model: class_index
            for class_index, group in enumerate(classes)
            for model in group
        }
        names = sorted(system.machines)

        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                exact = shortest_pairwise_separator(system, left, right)
                expected_distinguishable = class_by_model[left] != class_by_model[right]
                assert exact.distinguishable == expected_distinguishable
                if exact.sequence is not None:
                    assert traces_differ(system, left, right, exact.sequence)
                    assert brute_pair_minimum(
                        system, left, right, len(exact.sequence) - 1
                    ) is None
                pair_checks += 1

        adaptive = synthesize_adaptive_policy(system, max_beliefs=10_000)
        assert adaptive.exact
        if adaptive.status == "solved":
            depth = adaptive.worst_case_steps
            assert depth is not None
            assert brute_adaptive_solvable(system, system.initial_belief, depth, {})
            if depth > 0:
                assert not brute_adaptive_solvable(system, system.initial_belief, depth - 1, {})
        else:
            # In a one-state system, repeating an action never changes future
            # behavior. Therefore a depth of |A| exhausts all useful tests.
            assert not brute_adaptive_solvable(
                system, system.initial_belief, len(system.actions), {}
            )
        adaptive_checks += 1

        preset = synthesize_preset_sequence(system, max_partitions=10_000)
        assert preset.exact
        if preset.status == "solved":
            sequence = preset.sequence
            assert sequence is not None
            assert brute_preset_solvable(system, len(sequence))
            if sequence:
                assert not brute_preset_solvable(system, len(sequence) - 1)
        else:
            assert not brute_preset_solvable(system, len(system.actions))
        preset_checks += 1

    # Dynamic two-candidate machines validate product-state reachability and
    # shortest delayed separators against partition-refinement equivalence.
    for _ in range(DYNAMIC_PAIR_CASES):
        system = random_dynamic_pair(rng)
        classes = initial_behavioral_classes(system)
        exact = shortest_pairwise_separator(system, "H0", "H1")
        expected_distinguishable = len(classes) == 2
        assert exact.distinguishable == expected_distinguishable
        if exact.sequence is not None:
            assert traces_differ(system, "H0", "H1", exact.sequence)
            assert brute_pair_minimum(
                system, "H0", "H1", len(exact.sequence) - 1
            ) is None
        pair_checks += 1

    return ValidationSummary(
        static_cases=STATIC_CASES,
        dynamic_pair_cases=DYNAMIC_PAIR_CASES,
        pair_checks=pair_checks,
        adaptive_checks=adaptive_checks,
        preset_checks=preset_checks,
    )


if __name__ == "__main__":
    summary = run()
    print(f"seed={SEED}")
    print(f"static systems={summary.static_cases}")
    print(f"dynamic pair systems={summary.dynamic_pair_cases}")
    print(f"pairwise checks={summary.pair_checks}")
    print(f"adaptive checks={summary.adaptive_checks}")
    print(f"preset checks={summary.preset_checks}")
