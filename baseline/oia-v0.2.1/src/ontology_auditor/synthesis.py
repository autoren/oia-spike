"""Exact adaptive and preset intervention synthesis over finite candidates."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .model import (
    Belief,
    CandidateSystem,
    ModelValidationError,
    World,
    belief_models,
    canonical_belief,
)


TerminalPredicate = Callable[[Belief], bool]
LeafDescription = Callable[[Belief], str]


class CertificateValidationError(ValueError):
    """Raised when a policy or impossibility certificate is not sound."""


def _belief_to_dict(belief: Belief) -> list[dict[str, str]]:
    return [
        {"model": world.model, "state": world.state}
        for world in belief
    ]


def _belief_from_dict(payload: object) -> Belief:
    if not isinstance(payload, list):
        raise CertificateValidationError("serialized belief must be a list")
    worlds: list[World] = []
    for raw_world in payload:
        if not isinstance(raw_world, Mapping):
            raise CertificateValidationError(
                "serialized belief worlds must be objects"
            )
        try:
            model = str(raw_world["model"])
            state = str(raw_world["state"])
        except KeyError as exc:
            raise CertificateValidationError(
                f"serialized world missing {exc.args[0]!r}"
            ) from exc
        worlds.append(World(model, state))
    try:
        belief = canonical_belief(worlds)
    except ModelValidationError as exc:
        raise CertificateValidationError(str(exc)) from exc
    if len(belief) != len(worlds):
        raise CertificateValidationError(
            "serialized belief contains duplicate model/state worlds"
        )
    return belief


@dataclass(frozen=True)
class BlockingStep:
    """One adversarial successor that keeps a belief inside the losing set."""

    belief: Belief
    action: str
    output: str
    successor: Belief

    def to_dict(self) -> dict[str, object]:
        return {
            "belief": _belief_to_dict(self.belief),
            "action": self.action,
            "output": self.output,
            "successor": _belief_to_dict(self.successor),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BlockingStep":
        try:
            belief = _belief_from_dict(payload["belief"])
            action = str(payload["action"])
            output = str(payload["output"])
            successor = _belief_from_dict(payload["successor"])
        except KeyError as exc:
            raise CertificateValidationError(
                f"serialized blocker missing {exc.args[0]!r}"
            ) from exc
        return cls(belief, action, output, successor)


@dataclass(frozen=True)
class AdaptiveImpossibilityCertificate:
    """A closed losing set proving that no finite guaranteed policy exists.

    Every belief in the set is nonterminal. For every permitted action, the
    certificate supplies at least one possible observation successor that also
    lies in the set. Therefore an adversarially selected true candidate can
    keep any adaptive policy unresolved forever.
    """

    losing_beliefs: tuple[Belief, ...]
    blockers: tuple[BlockingStep, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "closed_losing_set",
            "losing_beliefs": [
                _belief_to_dict(belief) for belief in self.losing_beliefs
            ],
            "blocking_successors": [blocker.to_dict() for blocker in self.blockers],
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "AdaptiveImpossibilityCertificate":
        if payload.get("type") != "closed_losing_set":
            raise CertificateValidationError(
                "serialized certificate has the wrong type"
            )
        raw_beliefs = payload.get("losing_beliefs")
        raw_blockers = payload.get("blocking_successors")
        if not isinstance(raw_beliefs, list) or not isinstance(raw_blockers, list):
            raise CertificateValidationError(
                "serialized certificate must contain belief and blocker lists"
            )
        beliefs = tuple(_belief_from_dict(item) for item in raw_beliefs)
        blockers: list[BlockingStep] = []
        for item in raw_blockers:
            if not isinstance(item, Mapping):
                raise CertificateValidationError(
                    "serialized blocking successors must be objects"
                )
            blockers.append(BlockingStep.from_dict(item))
        return cls(beliefs, tuple(blockers))


@dataclass
class PolicyNode:
    """An adaptive experiment tree.

    Internal nodes select an action. Branch keys are observed outputs. Leaves
    contain a human-readable conclusion and the surviving candidates.
    """

    action: str | None = None
    conclusion: str | None = None
    candidates: tuple[str, ...] = ()
    branches: dict[str, "PolicyNode"] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return self.action is None

    def to_dict(self) -> dict[str, object]:
        if self.is_leaf:
            return {
                "type": "leaf",
                "conclusion": self.conclusion,
                "candidates": list(self.candidates),
            }
        return {
            "type": "action",
            "action": self.action,
            "branches": {
                output: child.to_dict() for output, child in sorted(self.branches.items())
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PolicyNode":
        node_type = payload.get("type")
        if node_type == "leaf":
            raw_candidates = payload.get("candidates", [])
            if not isinstance(raw_candidates, list):
                raise CertificateValidationError(
                    "serialized leaf candidates must be a list"
                )
            conclusion = payload.get("conclusion")
            return cls(
                conclusion=None if conclusion is None else str(conclusion),
                candidates=tuple(str(item) for item in raw_candidates),
            )
        if node_type == "action":
            if "action" not in payload:
                raise CertificateValidationError(
                    "serialized action node is missing its action"
                )
            raw_branches = payload.get("branches")
            if not isinstance(raw_branches, Mapping):
                raise CertificateValidationError(
                    "serialized action branches must be an object"
                )
            branches: dict[str, PolicyNode] = {}
            for output, child in raw_branches.items():
                if not isinstance(child, Mapping):
                    raise CertificateValidationError(
                        "serialized policy children must be objects"
                    )
                branches[str(output)] = cls.from_dict(child)
            return cls(action=str(payload["action"]), branches=branches)
        raise CertificateValidationError(
            f"serialized policy node has unknown type {node_type!r}"
        )


@dataclass(frozen=True)
class AdaptiveSynthesisResult:
    """Result of adaptive synthesis with explicit cap semantics.

    ``status="solved"`` is reserved for a globally minimum-worst-case policy
    obtained after complete reachable-belief enumeration.

    ``status="witness"`` carries a sound terminating policy found from an
    incomplete, cap-limited graph.  Its ``worst_case_steps`` is the verified
    depth of that witness and therefore only an upper bound on the unknown
    global minimum.

    ``status="impossible"`` is returned only with complete enumeration and a
    closed-losing-set certificate.  A cap-limited run can never report
    impossibility.  ``status="unknown"`` means that the cap stopped the search
    before either a policy witness or an impossibility certificate was found.
    """

    status: str
    exact: bool
    enumeration_complete: bool
    optimality_certified: bool
    depth_claim: str | None
    worst_case_steps: int | None
    reachable_beliefs: int
    policy: PolicyNode | None
    impossibility_certificate: AdaptiveImpossibilityCertificate | None
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "exact": self.exact,
            "enumeration_complete": self.enumeration_complete,
            "optimality_certified": self.optimality_certified,
            "depth_claim": self.depth_claim,
            "worst_case_steps": self.worst_case_steps,
            "reachable_beliefs": self.reachable_beliefs,
            "reason": self.reason,
            "policy": self.policy.to_dict() if self.policy else None,
            "impossibility_certificate": (
                self.impossibility_certificate.to_dict()
                if self.impossibility_certificate
                else None
            ),
        }


@dataclass(frozen=True)
class PresetSynthesisResult:
    status: str
    exact: bool
    sequence: tuple[str, ...] | None
    explored_partitions: int
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "exact": self.exact,
            "sequence": list(self.sequence) if self.sequence is not None else None,
            "length": len(self.sequence) if self.sequence is not None else None,
            "explored_partitions": self.explored_partitions,
            "reason": self.reason,
        }


def identify_models_terminal(belief: Belief) -> bool:
    return len(belief) <= 1


def identify_models_description(belief: Belief) -> str:
    if not belief:
        return "no candidate remains"
    if len(belief) == 1:
        return f"identified candidate {belief[0].model}"
    return f"unresolved candidates: {', '.join(belief_models(belief))}"


def label_terminal(labels: Mapping[str, str]) -> TerminalPredicate:
    def predicate(belief: Belief) -> bool:
        return len({labels[world.model] for world in belief}) <= 1

    return predicate


def label_description(labels: Mapping[str, str]) -> LeafDescription:
    def describe(belief: Belief) -> str:
        values = sorted({labels[world.model] for world in belief})
        if len(values) == 1:
            return f"identified target class {values[0]}"
        return f"unresolved target classes: {', '.join(values)}"

    return describe


def _reachable_beliefs(
    system: CandidateSystem,
    terminal: TerminalPredicate,
    max_beliefs: int,
) -> tuple[set[Belief], bool]:
    initial = system.initial_belief
    seen: set[Belief] = {initial}
    queue: deque[Belief] = deque([initial])

    while queue:
        belief = queue.popleft()
        if terminal(belief):
            continue
        for action in system.actions:
            for successor in system.step_belief(belief, action).values():
                if successor in seen:
                    continue
                if len(seen) >= max_beliefs:
                    return seen, False
                seen.add(successor)
                queue.append(successor)
    return seen, True


def synthesize_adaptive_policy(
    system: CandidateSystem,
    terminal: TerminalPredicate = identify_models_terminal,
    describe_leaf: LeafDescription = identify_models_description,
    *,
    max_beliefs: int = 100_000,
) -> AdaptiveSynthesisResult:
    """Synthesize a minimum-worst-case terminating adaptive policy.

    The algorithm first enumerates the finite reachable belief graph and then
    computes its least terminating attractor. When enumeration completes, a
    positive result is a constructive witness and a negative result is an exact
    no-policy certificate for the supplied action/observation interface.
    """

    reachable, complete = _reachable_beliefs(system, terminal, max_beliefs)
    ordered_reachable = tuple(sorted(reachable))
    rank: dict[Belief, int] = {
        belief: 0 for belief in ordered_reachable if terminal(belief)
    }

    # Compute only the least terminating rank during attractor construction.
    # Belief iteration is canonical so the implementation is reproducible, but
    # the rank fixed point itself does not depend on discovery order.
    changed = True
    while changed:
        changed = False
        for belief in ordered_reachable:
            if terminal(belief):
                continue
            best_depth: int | None = None
            for action in system.actions:
                successors = tuple(system.step_belief(belief, action).values())
                if not successors or any(successor not in rank for successor in successors):
                    continue
                candidate_depth = 1 + max(rank[successor] for successor in successors)
                if best_depth is None or candidate_depth < best_depth:
                    best_depth = candidate_depth
            if best_depth is not None and (
                belief not in rank or best_depth < rank[belief]
            ):
                rank[belief] = best_depth
                changed = True

    # Select a canonical action only after the final rank map is known. This
    # prevents an equal-depth action discovered in a later attractor pass from
    # being ignored because the belief's numeric rank did not improve. Among all
    # minimum-depth actions, the lexicographically smallest action is chosen.
    choice: dict[Belief, str] = {}
    for belief in ordered_reachable:
        if belief not in rank or terminal(belief):
            continue
        optimal_actions: list[str] = []
        for action in system.actions:
            successors = tuple(system.step_belief(belief, action).values())
            if not successors or any(successor not in rank for successor in successors):
                continue
            candidate_depth = 1 + max(rank[successor] for successor in successors)
            if candidate_depth == rank[belief]:
                optimal_actions.append(action)
        if not optimal_actions:
            raise RuntimeError(
                "internal error: ranked belief has no rank-preserving action"
            )
        choice[belief] = min(optimal_actions)

    initial = system.initial_belief
    if initial not in rank:
        if complete:
            losing = reachable - set(rank)
            blockers: list[BlockingStep] = []
            for belief in sorted(losing, key=repr):
                for action in system.actions:
                    successors = system.step_belief(belief, action)
                    blocking = [
                        (output, successor)
                        for output, successor in successors.items()
                        if successor in losing
                    ]
                    if not blocking:
                        raise RuntimeError(
                            "internal error: losing-set certificate is not closed"
                        )
                    output, successor = min(blocking, key=repr)
                    blockers.append(
                        BlockingStep(belief, action, output, successor)
                    )
            certificate = AdaptiveImpossibilityCertificate(
                losing_beliefs=tuple(sorted(losing, key=repr)),
                blockers=tuple(blockers),
            )
            return AdaptiveSynthesisResult(
                status="impossible",
                exact=True,
                enumeration_complete=True,
                optimality_certified=False,
                depth_claim=None,
                worst_case_steps=None,
                reachable_beliefs=len(reachable),
                policy=None,
                impossibility_certificate=certificate,
                reason=(
                    "the complete reachable belief graph contains no terminating adaptive "
                    "policy for the requested target"
                ),
            )
        return AdaptiveSynthesisResult(
            status="unknown",
            exact=False,
            enumeration_complete=False,
            optimality_certified=False,
            depth_claim=None,
            worst_case_steps=None,
            reachable_beliefs=len(reachable),
            policy=None,
            impossibility_certificate=None,
            reason=f"belief enumeration reached the configured limit of {max_beliefs}",
        )

    def build(belief: Belief) -> PolicyNode:
        if terminal(belief):
            return PolicyNode(
                conclusion=describe_leaf(belief),
                candidates=belief_models(belief),
            )
        action = choice[belief]
        node = PolicyNode(action=action)
        for output, successor in system.step_belief(belief, action).items():
            if rank[successor] >= rank[belief]:
                raise RuntimeError("internal error: reconstructed policy does not decrease rank")
            node.branches[output] = build(successor)
        return node

    return AdaptiveSynthesisResult(
        status="solved" if complete else "witness",
        exact=complete,
        enumeration_complete=complete,
        optimality_certified=complete,
        depth_claim="minimum" if complete else "witness_upper_bound",
        worst_case_steps=rank[initial],
        reachable_beliefs=len(reachable),
        policy=build(initial),
        impossibility_certificate=None,
        reason=(
            "minimum worst-case policy over the complete reachable belief graph"
            if complete
            else (
                "sound terminating policy found before reachable-belief enumeration "
                "hit its configured limit; reported depth is the verified witness "
                "depth, not a certified global minimum"
            )
        ),
    )


def verify_policy_witness(
    system: CandidateSystem,
    policy: PolicyNode,
    terminal: TerminalPredicate = identify_models_terminal,
) -> int:
    """Verify a policy tree and return its actual worst-case depth.

    The verifier recomputes every output branch from executable candidate
    semantics. It does not trust branch labels, leaf candidate lists, or the
    depth reported by the synthesizer.
    """

    active_nodes: set[int] = set()

    def visit(belief: Belief, node: PolicyNode) -> int:
        node_id = id(node)
        if node_id in active_nodes:
            raise CertificateValidationError("policy witness contains a cycle")
        active_nodes.add(node_id)
        try:
            if node.is_leaf:
                if not terminal(belief):
                    raise CertificateValidationError(
                        f"policy stops at unresolved belief {belief_models(belief)}"
                    )
                if tuple(sorted(node.candidates)) != belief_models(belief):
                    raise CertificateValidationError(
                        "leaf candidate list does not match executable belief"
                    )
                return 0

            if node.action not in system.actions:
                raise CertificateValidationError(
                    f"policy uses unknown action {node.action!r}"
                )
            expected = system.step_belief(belief, node.action)
            if set(node.branches) != set(expected):
                raise CertificateValidationError(
                    "policy branches do not exactly match possible observations"
                )
            return 1 + max(
                visit(successor, node.branches[output])
                for output, successor in expected.items()
            )
        finally:
            active_nodes.remove(node_id)

    return visit(system.initial_belief, policy)


def verify_adaptive_impossibility_certificate(
    system: CandidateSystem,
    certificate: AdaptiveImpossibilityCertificate,
    terminal: TerminalPredicate = identify_models_terminal,
) -> None:
    """Verify a closed-losing-set certificate without rerunning synthesis."""

    losing = set(certificate.losing_beliefs)
    if system.initial_belief not in losing:
        raise CertificateValidationError(
            "initial belief is absent from the claimed losing set"
        )
    if not losing:
        raise CertificateValidationError("claimed losing set is empty")
    for belief in losing:
        if terminal(belief):
            raise CertificateValidationError(
                "claimed losing set contains a terminal belief"
            )

    supplied: dict[tuple[Belief, str], BlockingStep] = {}
    for blocker in certificate.blockers:
        key = (blocker.belief, blocker.action)
        if key in supplied:
            raise CertificateValidationError(
                "certificate supplies duplicate blockers for one belief/action"
            )
        supplied[key] = blocker

    expected_keys = {
        (belief, action)
        for belief in losing
        for action in system.actions
    }
    if set(supplied) != expected_keys:
        raise CertificateValidationError(
            "certificate does not supply exactly one blocker per losing belief/action"
        )

    for (belief, action), blocker in supplied.items():
        branches = system.step_belief(belief, action)
        if blocker.output not in branches:
            raise CertificateValidationError(
                f"blocking output {blocker.output!r} is not executable"
            )
        if branches[blocker.output] != blocker.successor:
            raise CertificateValidationError(
                "blocking successor does not match executable semantics"
            )
        if blocker.successor not in losing:
            raise CertificateValidationError(
                "blocking successor leaves the claimed losing set"
            )


def verify_serialized_adaptive_result(
    system: CandidateSystem,
    payload: Mapping[str, Any],
    terminal: TerminalPredicate = identify_models_terminal,
) -> int | None:
    """Verify a serialized adaptive report artifact.

    The verifier checks executable witness/certificate soundness and enforces
    the metadata contract.  It returns the actual worst-case depth for both an
    exact ``solved`` policy and a cap-limited ``witness`` policy.  For a
    ``witness`` result that depth is *not* interpreted as globally minimal.

    A valid ``impossible`` result must be exact, complete, and carry a closed
    losing-set certificate.  A valid ``unknown`` result carries no conclusive
    artifact.
    """

    status = payload.get("status")
    exact = payload.get("exact")
    complete = payload.get("enumeration_complete")
    optimality = payload.get("optimality_certified")
    depth_claim = payload.get("depth_claim")
    raw_policy = payload.get("policy")
    raw_certificate = payload.get("impossibility_certificate")
    reported_depth = payload.get("worst_case_steps")

    if not isinstance(exact, bool):
        raise CertificateValidationError("adaptive result exact must be Boolean")
    if not isinstance(complete, bool):
        raise CertificateValidationError(
            "adaptive result enumeration_complete must be Boolean"
        )
    if not isinstance(optimality, bool):
        raise CertificateValidationError(
            "adaptive result optimality_certified must be Boolean"
        )

    if status in {"solved", "witness"}:
        expected = {
            "solved": (True, True, True, "minimum"),
            "witness": (False, False, False, "witness_upper_bound"),
        }[status]
        if (exact, complete, optimality, depth_claim) != expected:
            raise CertificateValidationError(
                f"{status} result has inconsistent exactness/optimality metadata"
            )
        if raw_certificate is not None:
            raise CertificateValidationError(
                f"{status} result must not carry an impossibility certificate"
            )
        if not isinstance(raw_policy, Mapping):
            raise CertificateValidationError(
                f"{status} adaptive result is missing a policy object"
            )
        policy = PolicyNode.from_dict(raw_policy)
        depth = verify_policy_witness(system, policy, terminal)
        if reported_depth is None or int(reported_depth) != depth:
            raise CertificateValidationError(
                "reported policy depth does not match the verified witness"
            )
        return depth

    if status == "impossible":
        if (exact, complete, optimality, depth_claim) != (True, True, False, None):
            raise CertificateValidationError(
                "impossible result must be exact and enumeration-complete"
            )
        if raw_policy is not None or reported_depth is not None:
            raise CertificateValidationError(
                "impossible result must not carry a policy or policy depth"
            )
        if not isinstance(raw_certificate, Mapping):
            raise CertificateValidationError(
                "impossible adaptive result is missing its certificate"
            )
        certificate = AdaptiveImpossibilityCertificate.from_dict(raw_certificate)
        verify_adaptive_impossibility_certificate(system, certificate, terminal)
        return None

    if status == "unknown":
        if (exact, complete, optimality, depth_claim) != (False, False, False, None):
            raise CertificateValidationError(
                "unknown result has inconsistent exactness metadata"
            )
        if raw_policy is not None or raw_certificate is not None or reported_depth is not None:
            raise CertificateValidationError(
                "unknown result must not carry a conclusive witness, certificate, or depth"
            )
        return None

    raise CertificateValidationError(
        f"serialized adaptive result has unknown status {status!r}"
    )


PartitionState = tuple[Belief, ...]


def _canonical_partition(blocks: list[Belief]) -> PartitionState:
    return tuple(sorted(blocks, key=repr))


def _advance_partition(
    system: CandidateSystem,
    partition: PartitionState,
    action: str,
) -> PartitionState:
    next_blocks: list[Belief] = []
    for block in partition:
        next_blocks.extend(system.step_belief(block, action).values())
    return _canonical_partition(next_blocks)


def synthesize_preset_sequence(
    system: CandidateSystem,
    terminal: TerminalPredicate = identify_models_terminal,
    *,
    max_partitions: int = 100_000,
) -> PresetSynthesisResult:
    """Find a shortest non-adaptive action sequence by breadth-first search."""

    start: PartitionState = (system.initial_belief,)

    def done(partition: PartitionState) -> bool:
        return all(terminal(block) for block in partition)

    if done(start):
        return PresetSynthesisResult("solved", True, (), 1, "target already resolved")

    queue: deque[tuple[PartitionState, tuple[str, ...]]] = deque([(start, ())])
    visited = {start}

    while queue:
        partition, prefix = queue.popleft()
        for action in system.actions:
            successor = _advance_partition(system, partition, action)
            sequence = prefix + (action,)
            if done(successor):
                return PresetSynthesisResult(
                    "solved",
                    True,
                    sequence,
                    len(visited),
                    "shortest fixed action sequence",
                )
            if successor in visited:
                continue
            if len(visited) >= max_partitions:
                return PresetSynthesisResult(
                    "unknown",
                    False,
                    None,
                    len(visited),
                    f"partition search reached the configured limit of {max_partitions}",
                )
            visited.add(successor)
            queue.append((successor, sequence))

    return PresetSynthesisResult(
        "impossible",
        True,
        None,
        len(visited),
        "the complete preset-experiment state graph contains no distinguishing sequence",
    )


def policy_path_lengths(system: CandidateSystem, policy: PolicyNode) -> Mapping[str, int]:
    """Return the number of interventions each candidate experiences."""

    lengths: dict[str, int] = {}
    for model_name, machine in system.machines.items():
        state = machine.initial_state
        node = policy
        steps = 0
        while not node.is_leaf:
            if node.action is None:
                raise RuntimeError("malformed policy node")
            transition = machine.step(state, node.action)
            state = transition.next_state
            steps += 1
            try:
                node = node.branches[transition.output]
            except KeyError as exc:
                raise RuntimeError(
                    f"policy has no branch for output {transition.output!r} from {model_name!r}"
                ) from exc
        lengths[model_name] = steps
    return lengths


def expected_policy_steps(
    system: CandidateSystem,
    policy: PolicyNode,
    priors: Mapping[str, float] | None = None,
) -> float:
    lengths = policy_path_lengths(system, policy)
    if priors is None:
        priors = {name: 1.0 for name in system.machines}
    total = sum(priors[name] for name in system.machines)
    if total <= 0:
        raise ValueError("prior mass must be positive")
    return sum(priors[name] * lengths[name] for name in system.machines) / total
