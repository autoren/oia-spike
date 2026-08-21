"""Behavioral equivalence and shortest pairwise separating experiments."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Mapping

from .model import CandidateSystem


Node = tuple[str, str]


@dataclass(frozen=True)
class PairwiseSeparation:
    left: str
    right: str
    distinguishable: bool
    sequence: tuple[str, ...] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "left": self.left,
            "right": self.right,
            "distinguishable": self.distinguishable,
            "sequence": list(self.sequence) if self.sequence is not None else None,
        }


def behavioral_partition(system: CandidateSystem) -> Mapping[Node, int]:
    """Compute exact trace-equivalence classes by partition refinement.

    Two nodes receive the same block exactly when every finite action sequence
    produces the same output sequence from those nodes.
    """

    nodes: list[Node] = [
        (machine.name, state)
        for machine in system.machines.values()
        for state in machine.states
    ]
    block: dict[Node, int] = {node: 0 for node in nodes}

    while True:
        # Refine *within* each existing block.  This makes the partition
        # monotone independently of the numeric IDs assigned to blocks.  A
        # previous implementation included the current block ID in a global
        # signature and compared the newly numbered mapping for exact equality.
        # On some cyclic machines the partition had stabilized while the IDs
        # kept changing, so the loop never terminated.
        groups_by_old_block: dict[int, list[Node]] = {}
        for node in nodes:
            groups_by_old_block.setdefault(block[node], []).append(node)

        refined: dict[Node, int] = {}
        split_occurred = False
        next_block = 0

        for old_block in sorted(groups_by_old_block):
            signature_groups: dict[tuple[tuple[str, int], ...], list[Node]] = {}
            for model_name, state in groups_by_old_block[old_block]:
                machine = system.machines[model_name]
                signature = tuple(
                    (
                        machine.step(state, action).output,
                        block[(model_name, machine.step(state, action).next_state)],
                    )
                    for action in system.actions
                )
                signature_groups.setdefault(signature, []).append((model_name, state))

            if len(signature_groups) > 1:
                split_occurred = True

            for signature in sorted(signature_groups, key=repr):
                for node in sorted(signature_groups[signature]):
                    refined[node] = next_block
                next_block += 1

        if not split_occurred:
            # Returning the existing mapping avoids treating harmless block-ID
            # renumbering as evidence that another refinement round is needed.
            return block
        block = refined


def initial_behavioral_classes(system: CandidateSystem) -> tuple[tuple[str, ...], ...]:
    partition = behavioral_partition(system)
    grouped: dict[int, list[str]] = {}
    for machine in system.machines.values():
        block = partition[(machine.name, machine.initial_state)]
        grouped.setdefault(block, []).append(machine.name)
    return tuple(
        tuple(sorted(models))
        for _, models in sorted(grouped.items(), key=lambda item: (item[0], item[1]))
    )


def shortest_pairwise_separator(
    system: CandidateSystem,
    left: str,
    right: str,
) -> PairwiseSeparation:
    """Return a shortest fixed input word separating two initial candidates.

    Breadth-first search is performed on the product state graph. If the graph
    closes without an output mismatch, the two candidates are behaviorally
    equivalent under every finite intervention sequence.
    """

    if left == right:
        return PairwiseSeparation(left, right, False, None)
    if left not in system.machines or right not in system.machines:
        missing = left if left not in system.machines else right
        raise KeyError(f"unknown candidate {missing!r}")

    left_machine = system.machines[left]
    right_machine = system.machines[right]
    start = (left_machine.initial_state, right_machine.initial_state)
    queue: deque[tuple[tuple[str, str], tuple[str, ...]]] = deque([(start, ())])
    visited = {start}

    while queue:
        (left_state, right_state), prefix = queue.popleft()
        for action in system.actions:
            left_transition = left_machine.step(left_state, action)
            right_transition = right_machine.step(right_state, action)
            sequence = prefix + (action,)
            if left_transition.output != right_transition.output:
                return PairwiseSeparation(left, right, True, sequence)
            successor = (left_transition.next_state, right_transition.next_state)
            if successor not in visited:
                visited.add(successor)
                queue.append((successor, sequence))

    return PairwiseSeparation(left, right, False, None)


def all_pairwise_separators(system: CandidateSystem) -> tuple[PairwiseSeparation, ...]:
    names = sorted(system.machines)
    return tuple(
        shortest_pairwise_separator(system, names[i], names[j])
        for i in range(len(names))
        for j in range(i + 1, len(names))
    )
