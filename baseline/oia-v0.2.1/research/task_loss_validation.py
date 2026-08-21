"""Independent exhaustive checks for model-dependent task-loss synthesis.

This validates the Pareto-frontier implementation against a deliberately
separate brute-force policy enumerator on tiny random systems. The instances
are small because the oracle retains every policy outcome vector without
Pareto pruning or memoized frontier compression.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from functools import lru_cache

from ontology_auditor import (
    CandidateSystem,
    DecisionProblem,
    MealyMachine,
    ModelActionLoss,
    Transition,
    synthesize_task_loss_policy,
)
from ontology_auditor.model import Belief, belief_models


SEED = 20260821
CASES = 250
DEPTH = 2


@dataclass(frozen=True)
class Summary:
    cases: int
    expected_checks: int
    robust_checks: int


def random_system(rng: random.Random) -> CandidateSystem:
    actions = ("a", "b")
    outputs = ("0", "1")
    machines = []
    for model_index in range(2):
        state_count = rng.randint(1, 2)
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
        machines.append(MealyMachine(f"H{model_index}", "s0", transitions))
    return CandidateSystem(machines)


def random_problem(
    rng: random.Random, system: CandidateSystem
) -> tuple[DecisionProblem, ModelActionLoss, dict[str, float]]:
    decisions = ("d0", "d1")
    utilities = {
        model: {decision: float(rng.randrange(0, 11)) for decision in decisions}
        for model in system.machines
    }
    losses = ModelActionLoss(
        {
            model: {
                action: rng.randrange(0, 501) / 100.0
                for action in system.actions
            }
            for model in system.machines
        }
    )
    priors = {
        model: float(rng.randrange(1, 10))
        for model in system.machines
    }
    return DecisionProblem(decisions, utilities), losses, priors


def brute_vectors(
    system: CandidateSystem,
    problem: DecisionProblem,
    losses: ModelActionLoss,
    initial: Belief,
    depth: int,
) -> tuple[tuple[float, ...], ...]:
    """Enumerate all policy outcome vectors, without dominance pruning."""

    @lru_cache(maxsize=None)
    def enumerate_at(belief: Belief, remaining: int) -> tuple[tuple[float, ...], ...]:
        models = belief_models(belief)
        entries: list[tuple[float, ...]] = [
            tuple(problem.utilities[model][decision] for model in models)
            for decision in problem.decisions
        ]
        if remaining == 0:
            return tuple(entries)

        model_index = {model: index for index, model in enumerate(models)}
        for action in system.actions:
            branches = tuple(sorted(system.step_belief(belief, action).items()))
            branch_vectors = [
                enumerate_at(successor, remaining - 1)
                for _, successor in branches
            ]
            for selected in itertools.product(*branch_vectors):
                vector = [0.0] * len(models)
                for (_, successor), child_values in zip(branches, selected):
                    for model, child_value in zip(
                        belief_models(successor), child_values
                    ):
                        vector[model_index[model]] = (
                            child_value - losses.get(model, action)
                        )
                entries.append(tuple(vector))
        return tuple(entries)

    return enumerate_at(initial, depth)


def expected_score(
    values: tuple[float, ...], models: tuple[str, ...], priors: dict[str, float]
) -> float:
    total = sum(priors[model] for model in models)
    return sum(
        priors[model] * value for model, value in zip(models, values)
    ) / total


def run() -> Summary:
    rng = random.Random(SEED)
    expected_checks = 0
    robust_checks = 0

    for _ in range(CASES):
        system = random_system(rng)
        problem, losses, priors = random_problem(rng, system)
        models = belief_models(system.initial_belief)
        oracle = brute_vectors(system, problem, losses, system.initial_belief, DEPTH)

        oracle_expected = max(expected_score(vector, models, priors) for vector in oracle)
        exact_expected = synthesize_task_loss_policy(
            system,
            problem,
            losses,
            criterion="expected",
            priors=priors,
            max_depth=DEPTH,
            max_frontier=100_000,
        )
        assert exact_expected.exact
        assert exact_expected.value is not None
        assert abs(exact_expected.value - oracle_expected) < 1e-9
        expected_checks += 1

        oracle_robust = max(min(vector) for vector in oracle)
        exact_robust = synthesize_task_loss_policy(
            system,
            problem,
            losses,
            criterion="robust",
            max_depth=DEPTH,
            max_frontier=100_000,
        )
        assert exact_robust.exact
        assert exact_robust.value is not None
        assert abs(exact_robust.value - oracle_robust) < 1e-9
        robust_checks += 1

    return Summary(CASES, expected_checks, robust_checks)


if __name__ == "__main__":
    summary = run()
    print(f"seed={SEED}")
    print(f"cases={summary.cases}")
    print(f"expected checks={summary.expected_checks}")
    print(f"robust checks={summary.robust_checks}")
