"""Exact task-loss-aware policy synthesis via Pareto outcome frontiers.

Unlike the lightweight scalar dynamic programs in :mod:`decision`, this module
allows the cost of an intervention to depend on the true candidate model. A
policy is represented by its complete vector of net outcomes, one component per
surviving candidate. Pareto pruning preserves every vector that can be optimal
for some monotone criterion, including Bayesian expectation and maximin value.

The method is exact within the declared depth when the frontier cap is not hit.
Its worst-case complexity is exponential in candidates, branches, and depth;
that cost is surfaced rather than hidden behind a heuristic approximation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import product
from typing import Mapping

from .decision import DecisionProblem
from .model import Belief, CandidateSystem, belief_models


@dataclass(frozen=True)
class ModelActionLoss:
    """Candidate-dependent intervention losses.

    ``losses[model][action]`` is charged when that action is applied while the
    corresponding candidate is the true world. v0.1 keeps losses independent of
    internal state; the policy-dependent observation kernel is already carried
    by the executable machine state.
    """

    losses: Mapping[str, Mapping[str, float]]

    def validate(self, system: CandidateSystem) -> None:
        missing_models = set(system.machines) - set(self.losses)
        if missing_models:
            raise ValueError(f"task losses missing candidates: {sorted(missing_models)}")
        for model in system.machines:
            missing_actions = set(system.actions) - set(self.losses[model])
            if missing_actions:
                raise ValueError(
                    f"task losses for {model!r} omit actions {sorted(missing_actions)}"
                )
            for action in system.actions:
                value = float(self.losses[model][action])
                if value < 0:
                    raise ValueError("task losses must be non-negative")

    def get(self, model: str, action: str) -> float:
        return float(self.losses[model][action])


@dataclass
class OutcomePolicyNode:
    action: str | None = None
    decision: str | None = None
    candidates: tuple[str, ...] = ()
    outcome_vector: dict[str, float] = field(default_factory=dict)
    branches: dict[str, "OutcomePolicyNode"] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return self.action is None

    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = {
            "outcome_vector": dict(sorted(self.outcome_vector.items())),
        }
        if self.is_leaf:
            base.update(
                {
                    "type": "decision",
                    "decision": self.decision,
                    "candidates": list(self.candidates),
                }
            )
        else:
            base.update(
                {
                    "type": "probe",
                    "action": self.action,
                    "branches": {
                        output: child.to_dict()
                        for output, child in sorted(self.branches.items())
                    },
                }
            )
        return base


@dataclass(frozen=True)
class FrontierEntry:
    values: tuple[float, ...]
    policy: OutcomePolicyNode


@dataclass(frozen=True)
class TaskLossPolicyResult:
    status: str
    exact: bool
    criterion: str
    max_depth: int
    value: float | None
    baseline_value: float
    value_of_information: float | None
    root_frontier_size: int
    largest_frontier_size: int
    policy: OutcomePolicyNode | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "exact": self.exact,
            "criterion": self.criterion,
            "max_depth": self.max_depth,
            "value": self.value,
            "baseline_value": self.baseline_value,
            "value_of_information": self.value_of_information,
            "root_frontier_size": self.root_frontier_size,
            "largest_frontier_size": self.largest_frontier_size,
            "reason": self.reason,
            "policy": self.policy.to_dict() if self.policy else None,
        }


def _dominates(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return all(a >= b for a, b in zip(left, right)) and any(
        a > b for a, b in zip(left, right)
    )


def _pareto_prune(entries: list[FrontierEntry]) -> list[FrontierEntry]:
    # Exact duplicate outcome vectors are interchangeable for every monotone
    # criterion; preserve the first deterministic construction.
    unique: dict[tuple[float, ...], FrontierEntry] = {}
    for entry in entries:
        unique.setdefault(entry.values, entry)
    candidates = list(unique.values())

    kept: list[FrontierEntry] = []
    for index, entry in enumerate(candidates):
        if any(
            other_index != index and _dominates(other.values, entry.values)
            for other_index, other in enumerate(candidates)
        ):
            continue
        kept.append(entry)
    return kept


def _score_expected(
    values: tuple[float, ...],
    models: tuple[str, ...],
    priors: Mapping[str, float],
) -> float:
    total = sum(priors[model] for model in models)
    if total <= 0:
        raise ValueError("candidate set has no positive prior mass")
    return sum(priors[model] * value for model, value in zip(models, values)) / total


def _score_robust(values: tuple[float, ...]) -> float:
    return min(values)


def synthesize_task_loss_policy(
    system: CandidateSystem,
    problem: DecisionProblem,
    task_losses: ModelActionLoss,
    *,
    criterion: str = "expected",
    priors: Mapping[str, float] | None = None,
    max_depth: int = 3,
    max_frontier: int = 50_000,
) -> TaskLossPolicyResult:
    """Compute an exact depth-bounded policy under model-dependent task loss.

    The returned result is exact if every reachable Pareto frontier is fully
    enumerated. If a frontier exceeds ``max_frontier``, synthesis fails closed
    with ``status='unknown'``; no approximate policy is silently substituted.
    """

    if criterion not in {"expected", "robust"}:
        raise ValueError("criterion must be 'expected' or 'robust'")
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if max_frontier <= 0:
        raise ValueError("max_frontier must be positive")
    task_losses.validate(system)

    missing_utilities = set(system.machines) - set(problem.utilities)
    if missing_utilities:
        raise ValueError(f"utilities missing candidates: {sorted(missing_utilities)}")

    if priors is None:
        priors = {model: 1.0 for model in system.machines}
    else:
        priors = {model: float(priors.get(model, 0.0)) for model in system.machines}
    if any(weight < 0 for weight in priors.values()) or sum(priors.values()) <= 0:
        raise ValueError("priors must be non-negative with positive total mass")

    largest_frontier = 0
    overflow_reason: str | None = None

    @lru_cache(maxsize=None)
    def frontier(belief: Belief, depth: int) -> tuple[FrontierEntry, ...]:
        nonlocal largest_frontier, overflow_reason
        models = belief_models(belief)
        entries: list[FrontierEntry] = []

        # Stop now and take a terminal decision.
        for decision in problem.decisions:
            values = tuple(problem.utilities[model][decision] for model in models)
            entries.append(
                FrontierEntry(
                    values=values,
                    policy=OutcomePolicyNode(
                        decision=decision,
                        candidates=models,
                        outcome_vector=dict(zip(models, values)),
                    ),
                )
            )

        if depth > 0 and overflow_reason is None:
            for action in system.actions:
                branches = system.step_belief(belief, action)
                ordered_branches = tuple(sorted(branches.items()))
                child_frontiers = [
                    frontier(successor, depth - 1)
                    for _, successor in ordered_branches
                ]
                if overflow_reason is not None:
                    break

                combination_count = 1
                for child in child_frontiers:
                    combination_count *= len(child)
                if combination_count > max_frontier:
                    overflow_reason = (
                        f"Cartesian branch frontier for belief {models}, action {action!r}, "
                        f"depth {depth} has {combination_count} combinations, exceeding "
                        f"max_frontier={max_frontier}"
                    )
                    break

                model_index = {model: index for index, model in enumerate(models)}
                for selected_children in product(*child_frontiers):
                    values = [0.0] * len(models)
                    child_nodes: dict[str, OutcomePolicyNode] = {}
                    for (output, successor), child in zip(
                        ordered_branches, selected_children
                    ):
                        child_models = belief_models(successor)
                        child_nodes[output] = child.policy
                        for child_model, child_value in zip(child_models, child.values):
                            values[model_index[child_model]] = (
                                child_value - task_losses.get(child_model, action)
                            )
                    vector = tuple(values)
                    entries.append(
                        FrontierEntry(
                            values=vector,
                            policy=OutcomePolicyNode(
                                action=action,
                                outcome_vector=dict(zip(models, vector)),
                                branches=child_nodes,
                            ),
                        )
                    )
                    if len(entries) > max_frontier * 4:
                        # Prune before the temporary list itself becomes an
                        # accidental memory denial of service.
                        entries = _pareto_prune(entries)
                        if len(entries) > max_frontier:
                            overflow_reason = (
                                f"Pareto frontier for belief {models}, depth {depth} "
                                f"exceeds max_frontier={max_frontier}"
                            )
                            break
                if overflow_reason is not None:
                    break

        pruned = _pareto_prune(entries)
        largest_frontier = max(largest_frontier, len(pruned))
        if len(pruned) > max_frontier and overflow_reason is None:
            overflow_reason = (
                f"Pareto frontier for belief {models}, depth {depth} has {len(pruned)} "
                f"entries, exceeding max_frontier={max_frontier}"
            )
        return tuple(pruned[:max_frontier])

    initial = system.initial_belief
    root_models = belief_models(initial)

    # Baseline permits no probes and is independent of frontier enumeration.
    terminal_vectors = [
        tuple(problem.utilities[model][decision] for model in root_models)
        for decision in problem.decisions
    ]
    if criterion == "expected":
        baseline = max(_score_expected(vector, root_models, priors) for vector in terminal_vectors)
    else:
        baseline = max(_score_robust(vector) for vector in terminal_vectors)

    root = frontier(initial, max_depth)
    if overflow_reason is not None:
        return TaskLossPolicyResult(
            status="unknown",
            exact=False,
            criterion=criterion,
            max_depth=max_depth,
            value=None,
            baseline_value=baseline,
            value_of_information=None,
            root_frontier_size=len(root),
            largest_frontier_size=largest_frontier,
            policy=None,
            reason=overflow_reason,
        )

    if criterion == "expected":
        scored = [
            (_score_expected(entry.values, root_models, priors), entry)
            for entry in root
        ]
    else:
        scored = [(_score_robust(entry.values), entry) for entry in root]
    value, best = max(scored, key=lambda item: (item[0], item[1].values))

    return TaskLossPolicyResult(
        status="solved",
        exact=True,
        criterion=criterion,
        max_depth=max_depth,
        value=value,
        baseline_value=baseline,
        value_of_information=value - baseline,
        root_frontier_size=len(root),
        largest_frontier_size=largest_frontier,
        policy=best.policy,
        reason="complete Pareto frontier enumerated within the declared depth",
    )
