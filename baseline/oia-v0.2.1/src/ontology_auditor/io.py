"""JSON loading helpers and audit schema parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .audit import AuditOptions, run_audit
from .decision import DecisionProblem
from .model import CandidateSystem
from .task_loss import ModelActionLoss


def load_payload(path: str | Path) -> Mapping[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("audit input must be a JSON object")
    return payload


def audit_payload(payload: Mapping[str, Any]) -> dict[str, object]:
    system = CandidateSystem.from_dict(payload)

    raw_labels = payload.get("labels")
    labels = None
    if raw_labels is not None:
        if not isinstance(raw_labels, Mapping):
            raise ValueError("labels must be an object")
        labels = {str(model): str(label) for model, label in raw_labels.items()}

    decision_problem = None
    raw_decisions = payload.get("decision_problem")
    if raw_decisions is not None:
        if not isinstance(raw_decisions, Mapping):
            raise ValueError("decision_problem must be an object")
        decisions = tuple(str(item) for item in raw_decisions["decisions"])
        raw_utilities = raw_decisions["utilities"]
        if not isinstance(raw_utilities, Mapping):
            raise ValueError("decision_problem.utilities must be an object")
        utilities = {
            str(model): {
                str(decision): float(value)
                for decision, value in by_decision.items()
            }
            for model, by_decision in raw_utilities.items()
        }
        decision_problem = DecisionProblem(decisions, utilities)

    raw_priors = payload.get("priors")
    priors = None
    if raw_priors is not None:
        if not isinstance(raw_priors, Mapping):
            raise ValueError("priors must be an object")
        priors = {str(model): float(value) for model, value in raw_priors.items()}

    raw_costs = payload.get("action_costs")
    action_costs = None
    if raw_costs is not None:
        if not isinstance(raw_costs, Mapping):
            raise ValueError("action_costs must be an object")
        action_costs = {str(action): float(value) for action, value in raw_costs.items()}

    raw_task_losses = payload.get("task_losses")
    task_losses = None
    if raw_task_losses is not None:
        if not isinstance(raw_task_losses, Mapping):
            raise ValueError("task_losses must be an object")
        parsed_losses: dict[str, dict[str, float]] = {}
        for raw_model, raw_by_action in raw_task_losses.items():
            if not isinstance(raw_by_action, Mapping):
                raise ValueError(
                    f"task_losses[{str(raw_model)!r}] must be an object"
                )
            parsed_losses[str(raw_model)] = {
                str(action): float(value)
                for action, value in raw_by_action.items()
            }
        task_losses = ModelActionLoss(parsed_losses)

    raw_options = payload.get("options", {})
    if not isinstance(raw_options, Mapping):
        raise ValueError("options must be an object")
    options = AuditOptions(
        max_beliefs=int(raw_options.get("max_beliefs", 100_000)),
        max_partitions=int(raw_options.get("max_partitions", 100_000)),
        value_depth=int(raw_options.get("value_depth", 4)),
        max_task_loss_frontier=int(
            raw_options.get("max_task_loss_frontier", 50_000)
        ),
    )

    return run_audit(
        system,
        labels=labels,
        decision_problem=decision_problem,
        priors=priors,
        action_costs=action_costs,
        task_losses=task_losses,
        options=options,
    )
