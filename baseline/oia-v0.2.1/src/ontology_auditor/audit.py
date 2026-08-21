"""High-level audit report composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .decision import (
    DecisionProblem,
    decision_description,
    decision_terminal,
    synthesize_expected_value_policy,
    synthesize_robust_value_policy,
)
from .equivalence import all_pairwise_separators, initial_behavioral_classes
from .model import CandidateSystem
from .task_loss import ModelActionLoss, synthesize_task_loss_policy
from .synthesis import (
    expected_policy_steps,
    label_description,
    label_terminal,
    synthesize_adaptive_policy,
    synthesize_preset_sequence,
)


@dataclass(frozen=True)
class AuditOptions:
    max_beliefs: int = 100_000
    max_partitions: int = 100_000
    value_depth: int = 4
    max_task_loss_frontier: int = 50_000


def run_audit(
    system: CandidateSystem,
    *,
    labels: Mapping[str, str] | None = None,
    decision_problem: DecisionProblem | None = None,
    priors: Mapping[str, float] | None = None,
    action_costs: Mapping[str, float] | None = None,
    task_losses: ModelActionLoss | None = None,
    options: AuditOptions = AuditOptions(),
) -> dict[str, object]:
    classes = initial_behavioral_classes(system)
    pairwise = all_pairwise_separators(system)

    identity_adaptive = synthesize_adaptive_policy(
        system,
        max_beliefs=options.max_beliefs,
    )
    identity_preset = synthesize_preset_sequence(
        system,
        max_partitions=options.max_partitions,
    )

    identity: dict[str, object] = {
        "adaptive": identity_adaptive.to_dict(),
        "preset": identity_preset.to_dict(),
    }
    if identity_adaptive.policy is not None:
        identity["adaptive_expected_steps"] = expected_policy_steps(
            system,
            identity_adaptive.policy,
            priors,
        )

    report: dict[str, object] = {
        "scope": {
            "semantics": "deterministic complete finite Mealy candidates",
            "candidate_count": len(system.machines),
            "state_count": sum(len(machine.states) for machine in system.machines.values()),
            "actions": list(system.actions),
        },
        "behavioral_equivalence_classes": [list(group) for group in classes],
        "pairwise_separation": [result.to_dict() for result in pairwise],
        "full_candidate_identification": identity,
    }

    if labels is not None:
        missing = set(system.machines) - set(labels)
        if missing:
            raise ValueError(f"labels missing candidates: {sorted(missing)}")
        target_adaptive = synthesize_adaptive_policy(
            system,
            terminal=label_terminal(labels),
            describe_leaf=label_description(labels),
            max_beliefs=options.max_beliefs,
        )
        target_preset = synthesize_preset_sequence(
            system,
            terminal=label_terminal(labels),
            max_partitions=options.max_partitions,
        )
        report["target_class_identification"] = {
            "labels": dict(labels),
            "adaptive": target_adaptive.to_dict(),
            "preset": target_preset.to_dict(),
            "cuts_behavioral_equivalence_class": any(
                len({labels[name] for name in group}) > 1 for group in classes
            ),
        }

    if decision_problem is not None:
        missing = set(system.machines) - set(decision_problem.utilities)
        if missing:
            raise ValueError(f"utilities missing candidates: {sorted(missing)}")
        decision_adaptive = synthesize_adaptive_policy(
            system,
            terminal=decision_terminal(decision_problem),
            describe_leaf=decision_description(decision_problem),
            max_beliefs=options.max_beliefs,
        )
        decision_preset = synthesize_preset_sequence(
            system,
            terminal=decision_terminal(decision_problem),
            max_partitions=options.max_partitions,
        )
        expected = synthesize_expected_value_policy(
            system,
            decision_problem,
            priors=priors,
            action_costs=action_costs,
            max_depth=options.value_depth,
        )
        robust = synthesize_robust_value_policy(
            system,
            decision_problem,
            action_costs=action_costs,
            max_depth=options.value_depth,
        )
        report["decision_relevance"] = {
            "decisions": list(decision_problem.decisions),
            "common_optimal_initially": sorted(
                decision_problem.common_optimal(system.initial_belief)
            ),
            "minimum_probe_to_common_optimum": {
                "adaptive": decision_adaptive.to_dict(),
                "preset": decision_preset.to_dict(),
            },
            "expected_value_policy": expected.to_dict(),
            "robust_value_policy": robust.to_dict(),
        }

        if task_losses is not None:
            task_loss_expected = synthesize_task_loss_policy(
                system,
                decision_problem,
                task_losses,
                criterion="expected",
                priors=priors,
                max_depth=options.value_depth,
                max_frontier=options.max_task_loss_frontier,
            )
            task_loss_robust = synthesize_task_loss_policy(
                system,
                decision_problem,
                task_losses,
                criterion="robust",
                max_depth=options.value_depth,
                max_frontier=options.max_task_loss_frontier,
            )
            report["decision_relevance"]["model_dependent_task_loss"] = {
                "expected_value_policy": task_loss_expected.to_dict(),
                "robust_value_policy": task_loss_robust.to_dict(),
            }

    return report
