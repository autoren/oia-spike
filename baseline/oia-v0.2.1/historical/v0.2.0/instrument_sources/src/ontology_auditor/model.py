"""Finite executable candidate models used by the intervention auditor.

The v0.1 core deliberately works at the behavioral boundary: each candidate
ontology must expose deterministic finite input/output semantics as a complete
Mealy machine. Richer symbolic programs can be audited after compiling their
bounded execution envelope to this representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


class ModelValidationError(ValueError):
    """Raised when a candidate machine is malformed or incompatible."""


@dataclass(frozen=True, order=True)
class Transition:
    """One deterministic action response."""

    output: str
    next_state: str


@dataclass(frozen=True, order=True)
class World:
    """A surviving candidate and its current internal execution state."""

    model: str
    state: str


Belief = tuple[World, ...]


@dataclass(frozen=True)
class MealyMachine:
    """A deterministic, complete finite-state transducer.

    Parameters
    ----------
    name:
        Unique candidate identifier. It is not treated as semantic evidence.
    initial_state:
        State used at the beginning of the audit.
    transitions:
        ``state -> action -> Transition`` mapping.
    metadata:
        Optional provenance or structural annotations. The core algorithms do
        not inspect this field.
    """

    name: str
    initial_state: str
    transitions: Mapping[str, Mapping[str, Transition]]
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ModelValidationError("machine name must be non-empty")
        if not self.transitions:
            raise ModelValidationError(f"machine {self.name!r} has no states")
        if self.initial_state not in self.transitions:
            raise ModelValidationError(
                f"machine {self.name!r} initial state {self.initial_state!r} is undefined"
            )

        actions: tuple[str, ...] | None = None
        for state, by_action in self.transitions.items():
            if not state:
                raise ModelValidationError(f"machine {self.name!r} has an empty state name")
            current_actions = tuple(sorted(by_action))
            if not current_actions:
                raise ModelValidationError(
                    f"machine {self.name!r} state {state!r} has no actions"
                )
            if actions is None:
                actions = current_actions
            elif current_actions != actions:
                raise ModelValidationError(
                    f"machine {self.name!r} is not input-complete: state {state!r} "
                    f"has actions {current_actions}, expected {actions}"
                )
            for action, transition in by_action.items():
                if not action:
                    raise ModelValidationError(
                        f"machine {self.name!r} state {state!r} has an empty action"
                    )
                if transition.next_state not in self.transitions:
                    raise ModelValidationError(
                        f"machine {self.name!r}: {state!r} --{action!r}--> "
                        f"undefined state {transition.next_state!r}"
                    )

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(sorted(self.transitions))

    @property
    def actions(self) -> tuple[str, ...]:
        first_state = next(iter(self.transitions))
        return tuple(sorted(self.transitions[first_state]))

    def step(self, state: str, action: str) -> Transition:
        try:
            return self.transitions[state][action]
        except KeyError as exc:
            raise ModelValidationError(
                f"undefined step in {self.name!r}: state={state!r}, action={action!r}"
            ) from exc

    def with_reset(self, action: str = "__reset__", output: str = "reset") -> "MealyMachine":
        """Return a copy with a reliable reset action from every state.

        This makes the reset assumption explicit in the executable interface
        instead of giving the synthesizer a hidden privilege.
        """

        if action in self.actions:
            raise ModelValidationError(
                f"cannot add reset action {action!r}; it already exists in {self.name!r}"
            )
        transitions: dict[str, dict[str, Transition]] = {}
        for state, by_action in self.transitions.items():
            transitions[state] = dict(by_action)
            transitions[state][action] = Transition(output=output, next_state=self.initial_state)
        return MealyMachine(
            name=self.name,
            initial_state=self.initial_state,
            transitions=transitions,
            metadata=self.metadata,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MealyMachine":
        try:
            name = str(payload["name"])
            initial_state = str(payload["initial_state"])
            raw_transitions = payload["transitions"]
        except KeyError as exc:
            raise ModelValidationError(f"missing machine field: {exc.args[0]}") from exc

        if not isinstance(raw_transitions, Mapping):
            raise ModelValidationError("transitions must be an object mapping states to actions")

        transitions: dict[str, dict[str, Transition]] = {}
        for raw_state, raw_by_action in raw_transitions.items():
            state = str(raw_state)
            if not isinstance(raw_by_action, Mapping):
                raise ModelValidationError(
                    f"transitions[{state!r}] must map actions to transition objects"
                )
            transitions[state] = {}
            for raw_action, raw_transition in raw_by_action.items():
                action = str(raw_action)
                if not isinstance(raw_transition, Mapping):
                    raise ModelValidationError(
                        f"transition {state!r}/{action!r} must be an object"
                    )
                try:
                    output = str(raw_transition["output"])
                    next_state = str(raw_transition["next_state"])
                except KeyError as exc:
                    raise ModelValidationError(
                        f"transition {state!r}/{action!r} missing {exc.args[0]!r}"
                    ) from exc
                transitions[state][action] = Transition(output, next_state)

        metadata = payload.get("metadata")
        if metadata is not None and not isinstance(metadata, Mapping):
            raise ModelValidationError("metadata must be an object when supplied")
        return cls(name, initial_state, transitions, metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "initial_state": self.initial_state,
            "transitions": {
                state: {
                    action: {
                        "output": transition.output,
                        "next_state": transition.next_state,
                    }
                    for action, transition in sorted(by_action.items())
                }
                for state, by_action in sorted(self.transitions.items())
            },
            "metadata": dict(self.metadata or {}),
        }


class CandidateSystem:
    """A compatible finite set of executable ontology hypotheses."""

    def __init__(self, machines: Sequence[MealyMachine]) -> None:
        if not machines:
            raise ModelValidationError("at least one candidate machine is required")
        names = [machine.name for machine in machines]
        if len(names) != len(set(names)):
            raise ModelValidationError("candidate machine names must be unique")

        reference_actions = machines[0].actions
        for machine in machines[1:]:
            if machine.actions != reference_actions:
                raise ModelValidationError(
                    f"machine {machine.name!r} has action alphabet {machine.actions}; "
                    f"expected {reference_actions}"
                )

        self._machines = {machine.name: machine for machine in machines}
        self._actions = reference_actions
        self._initial_belief = canonical_belief(
            World(machine.name, machine.initial_state) for machine in machines
        )

    @property
    def machines(self) -> Mapping[str, MealyMachine]:
        return self._machines

    @property
    def actions(self) -> tuple[str, ...]:
        return self._actions

    @property
    def initial_belief(self) -> Belief:
        return self._initial_belief

    def step_world(self, world: World, action: str) -> tuple[str, World]:
        transition = self._machines[world.model].step(world.state, action)
        return transition.output, World(world.model, transition.next_state)

    def step_belief(self, belief: Belief, action: str) -> dict[str, Belief]:
        """Apply an action and partition candidates by the observed output."""

        if action not in self._actions:
            raise ModelValidationError(f"unknown action {action!r}")
        raw: dict[str, list[World]] = {}
        for world in belief:
            output, successor = self.step_world(world, action)
            raw.setdefault(output, []).append(successor)
        return {
            output: canonical_belief(worlds)
            for output, worlds in sorted(raw.items(), key=lambda item: item[0])
        }

    def trace(self, model: str, actions: Iterable[str]) -> tuple[str, ...]:
        machine = self._machines[model]
        state = machine.initial_state
        outputs: list[str] = []
        for action in actions:
            transition = machine.step(state, action)
            outputs.append(transition.output)
            state = transition.next_state
        return tuple(outputs)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateSystem":
        raw_machines = payload.get("machines")
        if not isinstance(raw_machines, Sequence) or isinstance(raw_machines, (str, bytes)):
            raise ModelValidationError("top-level 'machines' must be an array")
        return cls([MealyMachine.from_dict(item) for item in raw_machines])


def canonical_belief(worlds: Iterable[World]) -> Belief:
    """Canonical, duplicate-free representation of a candidate belief."""

    by_model: dict[str, World] = {}
    for world in worlds:
        previous = by_model.get(world.model)
        if previous is not None and previous != world:
            raise ModelValidationError(
                "v0.1 supports one deterministic current state per candidate model; "
                f"model {world.model!r} appeared in states {previous.state!r} and {world.state!r}"
            )
        by_model[world.model] = world
    return tuple(sorted(by_model.values()))


def belief_models(belief: Belief) -> tuple[str, ...]:
    return tuple(world.model for world in belief)
