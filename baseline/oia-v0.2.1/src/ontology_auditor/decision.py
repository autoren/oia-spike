"""Decision relevance and depth-bounded value-of-information synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Mapping

from .model import Belief, CandidateSystem, belief_models
from .synthesis import LeafDescription, PolicyNode, TerminalPredicate


@dataclass(frozen=True)
class DecisionProblem:
    decisions: tuple[str, ...]
    utilities: Mapping[str, Mapping[str, float]]

    def __post_init__(self) -> None:
        if not self.decisions:
            raise ValueError("at least one terminal decision is required")
        for model, by_decision in self.utilities.items():
            missing = [decision for decision in self.decisions if decision not in by_decision]
            if missing:
                raise ValueError(f"utilities for {model!r} omit decisions {missing}")

    def optimal_decisions(self, model: str) -> frozenset[str]:
        by_decision = self.utilities[model]
        best = max(by_decision[decision] for decision in self.decisions)
        return frozenset(
            decision for decision in self.decisions if by_decision[decision] == best
        )

    def common_optimal(self, belief: Belief) -> frozenset[str]:
        common = set(self.decisions)
        for model in belief_models(belief):
            common.intersection_update(self.optimal_decisions(model))
        return frozenset(common)

    def robust_best(self, belief: Belief) -> tuple[str, float]:
        models = belief_models(belief)
        scored = [
            (
                min(self.utilities[model][decision] for model in models),
                decision,
            )
            for decision in self.decisions
        ]
        value, decision = max(scored, key=lambda item: (item[0], item[1]))
        return decision, value

    def expected_best(
        self,
        belief: Belief,
        priors: Mapping[str, float],
    ) -> tuple[str, float]:
        models = belief_models(belief)
        mass = sum(priors[model] for model in models)
        if mass <= 0:
            raise ValueError("belief has no positive prior mass")
        scored = [
            (
                sum(
                    priors[model] * self.utilities[model][decision]
                    for model in models
                )
                / mass,
                decision,
            )
            for decision in self.decisions
        ]
        value, decision = max(scored, key=lambda item: (item[0], item[1]))
        return decision, value


def decision_terminal(problem: DecisionProblem) -> TerminalPredicate:
    return lambda belief: bool(problem.common_optimal(belief))


def decision_description(problem: DecisionProblem) -> LeafDescription:
    def describe(belief: Belief) -> str:
        common = sorted(problem.common_optimal(belief))
        if common:
            return f"common-optimal decision(s): {', '.join(common)}"
        return "no common-optimal terminal decision"

    return describe


@dataclass
class DecisionPolicyNode:
    action: str | None = None
    decision: str | None = None
    conditional_value: float = 0.0
    candidates: tuple[str, ...] = ()
    branches: dict[str, "DecisionPolicyNode"] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return self.action is None

    def to_dict(self) -> dict[str, object]:
        if self.is_leaf:
            return {
                "type": "decision",
                "decision": self.decision,
                "conditional_value": self.conditional_value,
                "candidates": list(self.candidates),
            }
        return {
            "type": "probe",
            "action": self.action,
            "conditional_value": self.conditional_value,
            "branches": {
                output: child.to_dict() for output, child in sorted(self.branches.items())
            },
        }


@dataclass(frozen=True)
class ValuePolicyResult:
    criterion: str
    max_depth: int
    value: float
    baseline_value: float
    value_of_information: float
    policy: DecisionPolicyNode

    def to_dict(self) -> dict[str, object]:
        return {
            "criterion": self.criterion,
            "max_depth": self.max_depth,
            "value": self.value,
            "baseline_value": self.baseline_value,
            "value_of_information": self.value_of_information,
            "policy": self.policy.to_dict(),
        }


def _validate_action_costs(
    system: CandidateSystem,
    action_costs: Mapping[str, float] | None,
) -> dict[str, float]:
    if action_costs is None:
        return {action: 0.0 for action in system.actions}
    unknown = set(action_costs) - set(system.actions)
    if unknown:
        raise ValueError(f"costs supplied for unknown actions: {sorted(unknown)}")
    result = {action: float(action_costs.get(action, 0.0)) for action in system.actions}
    if any(cost < 0 for cost in result.values()):
        raise ValueError("v0.1 requires non-negative intervention costs")
    return result


def synthesize_expected_value_policy(
    system: CandidateSystem,
    problem: DecisionProblem,
    *,
    priors: Mapping[str, float] | None = None,
    action_costs: Mapping[str, float] | None = None,
    max_depth: int = 4,
) -> ValuePolicyResult:
    """Exact Bayes-optimal probe-or-decide policy within ``max_depth``."""

    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if priors is None:
        priors = {name: 1.0 for name in system.machines}
    else:
        priors = {name: float(priors.get(name, 0.0)) for name in system.machines}
    if any(weight < 0 for weight in priors.values()) or sum(priors.values()) <= 0:
        raise ValueError("priors must be non-negative with positive total mass")
    costs = _validate_action_costs(system, action_costs)

    @lru_cache(maxsize=None)
    def solve(belief: Belief, depth: int) -> tuple[float, str, object]:
        decision, stop_value = problem.expected_best(belief, priors)
        best_value = stop_value
        best_kind = "decision"
        best_payload: object = decision

        if depth > 0:
            models = belief_models(belief)
            mass = sum(priors[model] for model in models)
            for action in system.actions:
                branches = system.step_belief(belief, action)
                action_value = -costs[action]
                for successor in branches.values():
                    branch_mass = sum(priors[model] for model in belief_models(successor))
                    successor_value, _, _ = solve(successor, depth - 1)
                    action_value += (branch_mass / mass) * successor_value
                # Strict improvement makes stopping the stable tie-break.
                if action_value > best_value + 1e-12:
                    best_value = action_value
                    best_kind = "action"
                    best_payload = action
        return best_value, best_kind, best_payload

    def build(belief: Belief, depth: int) -> DecisionPolicyNode:
        value, kind, payload = solve(belief, depth)
        if kind == "decision":
            return DecisionPolicyNode(
                decision=str(payload),
                conditional_value=value,
                candidates=belief_models(belief),
            )
        action = str(payload)
        node = DecisionPolicyNode(action=action, conditional_value=value)
        for output, successor in system.step_belief(belief, action).items():
            node.branches[output] = build(successor, depth - 1)
        return node

    initial = system.initial_belief
    _, baseline = problem.expected_best(initial, priors)
    value, _, _ = solve(initial, max_depth)
    return ValuePolicyResult(
        criterion="expected",
        max_depth=max_depth,
        value=value,
        baseline_value=baseline,
        value_of_information=value - baseline,
        policy=build(initial, max_depth),
    )


def synthesize_robust_value_policy(
    system: CandidateSystem,
    problem: DecisionProblem,
    *,
    action_costs: Mapping[str, float] | None = None,
    max_depth: int = 4,
) -> ValuePolicyResult:
    """Exact maximin probe-or-decide policy within ``max_depth``."""

    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    costs = _validate_action_costs(system, action_costs)

    @lru_cache(maxsize=None)
    def solve(belief: Belief, depth: int) -> tuple[float, str, object]:
        decision, stop_value = problem.robust_best(belief)
        best_value = stop_value
        best_kind = "decision"
        best_payload: object = decision

        if depth > 0:
            for action in system.actions:
                branches = system.step_belief(belief, action)
                action_value = -costs[action] + min(
                    solve(successor, depth - 1)[0] for successor in branches.values()
                )
                if action_value > best_value + 1e-12:
                    best_value = action_value
                    best_kind = "action"
                    best_payload = action
        return best_value, best_kind, best_payload

    def build(belief: Belief, depth: int) -> DecisionPolicyNode:
        value, kind, payload = solve(belief, depth)
        if kind == "decision":
            return DecisionPolicyNode(
                decision=str(payload),
                conditional_value=value,
                candidates=belief_models(belief),
            )
        action = str(payload)
        node = DecisionPolicyNode(action=action, conditional_value=value)
        for output, successor in system.step_belief(belief, action).items():
            node.branches[output] = build(successor, depth - 1)
        return node

    initial = system.initial_belief
    _, baseline = problem.robust_best(initial)
    value, _, _ = solve(initial, max_depth)
    return ValuePolicyResult(
        criterion="robust",
        max_depth=max_depth,
        value=value,
        baseline_value=baseline,
        value_of_information=value - baseline,
        policy=build(initial, max_depth),
    )


def policy_to_identification_tree(policy: DecisionPolicyNode) -> PolicyNode:
    """Convert a decision policy to the generic display structure."""

    if policy.is_leaf:
        return PolicyNode(
            conclusion=f"choose {policy.decision}",
            candidates=policy.candidates,
        )
    node = PolicyNode(action=policy.action)
    node.branches = {
        output: policy_to_identification_tree(child)
        for output, child in policy.branches.items()
    }
    return node
