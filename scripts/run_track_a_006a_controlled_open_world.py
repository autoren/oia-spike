#!/usr/bin/env python3
"""Run the frozen Track A 006a controlled open-world diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Callable
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "baseline" / "oia-v0.2.1"
sys.path.insert(0, str(BASELINE / "src"))

from ontology_auditor import (  # noqa: E402
    CandidateSystem,
    MealyMachine,
    PolicyNode,
    Transition,
    initial_behavioral_classes,
    synthesize_adaptive_policy,
)
from ontology_auditor.model import Belief, World, belief_models  # noqa: E402


AUDIT_ROOT = ROOT / "audits" / "track-a-006a"
PROTOCOL_PATH = AUDIT_ROOT / "CONTROLLED_OPEN_WORLD_PROTOCOL.frozen.json"
BENCHMARK_MASTER_SEED = "oia-track-a-006a-benchmark-v1"
FIXTURE_MASTER_SEED = "oia-track-a-006a-fixture-v1"
EXPECTED_BASELINE_HASHES = {
    "baseline/oia-v0.2.1/src/ontology_auditor/__init__.py": "321863cc19ba7b6bb22593aa3f20f991cbbd12930afbff4dc9dccf4cc7b15a3b",
    "baseline/oia-v0.2.1/src/ontology_auditor/model.py": "9d622641f267e7dc1e99302060ac0a3a7ecd654e46f3162c9605c9ba602eca24",
    "baseline/oia-v0.2.1/src/ontology_auditor/synthesis.py": "7df543e8af759a26ea2d5c256de4a66fb60a33dc3a42b2fea0d720c430f21f07",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def derived_seed(master: str, *parts: object) -> int:
    framed = "\0".join([master, *(str(part) for part in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(framed).digest()[:8], "big")


def machine_hash(machine: MealyMachine) -> str:
    return sha256_bytes(pretty_bytes(machine.to_dict()))


def random_delayed_machine(
    name: str,
    seed: int,
    *,
    state_count: int,
    action_count: int,
    output_count: int,
) -> MealyMachine:
    """Generate a complete machine whose first observations are uninformative."""
    rng = random.Random(seed)
    states = tuple(f"s{index}" for index in range(state_count))
    actions = tuple(f"a{index}" for index in range(action_count))
    outputs = tuple(f"o{index}" for index in range(output_count))
    transitions: dict[str, dict[str, Transition]] = {}
    for state_index, state in enumerate(states):
        transitions[state] = {}
        for action in actions:
            output = outputs[0] if state_index == 0 else rng.choice(outputs)
            transitions[state][action] = Transition(
                output=output,
                next_state=rng.choice(states),
            )
    return MealyMachine(name=name, initial_state="s0", transitions=transitions)


def benchmark_config(protocol: dict[str, Any]) -> dict[str, Any]:
    config = dict(protocol["benchmark"])
    if config["master_seed"] != BENCHMARK_MASTER_SEED:
        raise ValueError("006a benchmark seed changed")
    return config


def fixture_config() -> dict[str, Any]:
    return {
        "master_seed": FIXTURE_MASTER_SEED,
        "case_count": 3,
        "candidate_count": 4,
        "state_count": 3,
        "action_count": 3,
        "output_count": 3,
        "minimum_oia_depth": 2,
        "maximum_oia_depth": 6,
        "maximum_generation_attempts_per_case": 2000,
        "max_beliefs": 100000,
        "random_trials_per_target": 4,
    }


def preflight() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status_at_freeze"] != "frozen_before_benchmark_case_generation_or_target_execution":
        raise ValueError("006a prospective ordering changed")
    if benchmark_config(protocol)["master_seed"] == FIXTURE_MASTER_SEED:
        raise ValueError("006a benchmark and fixture seeds overlap")
    observed = {}
    for relative, expected in EXPECTED_BASELINE_HASHES.items():
        digest = sha256_file(ROOT / relative)
        if digest != expected:
            raise ValueError(f"006a baseline changed: {relative}")
        observed[relative] = digest
    return {
        "audit_id": "OIA-1-TRACK-A-006a",
        "baseline_hashes": observed,
        "benchmark_cases_generated": 0,
        "benchmark_targets_executed": 0,
        "pass": True,
        "status": "controlled_open_world_preflight_passed",
    }


def generate_case(
    config: dict[str, Any], case_index: int
) -> tuple[CandidateSystem, MealyMachine, Any, dict[str, Any]]:
    master = config["master_seed"]
    rejection_counts: Counter[str] = Counter()
    accepted_attempt = None
    system = None
    adaptive = None
    for attempt in range(config["maximum_generation_attempts_per_case"]):
        candidates = [
            random_delayed_machine(
                f"H{candidate_index}",
                derived_seed(master, "candidate", case_index, attempt, candidate_index),
                state_count=config["state_count"],
                action_count=config["action_count"],
                output_count=config["output_count"],
            )
            for candidate_index in range(config["candidate_count"])
        ]
        candidate_system = CandidateSystem(candidates)
        if len(initial_behavioral_classes(candidate_system)) != config["candidate_count"]:
            rejection_counts["candidate_behavioral_equivalence"] += 1
            continue
        result = synthesize_adaptive_policy(
            candidate_system, max_beliefs=config["max_beliefs"]
        )
        if result.status != "solved" or not result.exact or result.policy is None:
            rejection_counts[f"oia_{result.status}"] += 1
            continue
        depth = result.worst_case_steps
        if depth is None or not config["minimum_oia_depth"] <= depth <= config["maximum_oia_depth"]:
            rejection_counts["oia_depth_out_of_range"] += 1
            continue
        system = candidate_system
        adaptive = result
        accepted_attempt = attempt
        break
    if system is None or adaptive is None or accepted_attempt is None:
        raise RuntimeError(f"006a could not generate candidate case {case_index}")

    outside = None
    outside_attempt = None
    for attempt in range(config["maximum_generation_attempts_per_case"]):
        target = random_delayed_machine(
            "OUTSIDE",
            derived_seed(master, "outside", case_index, attempt),
            state_count=config["state_count"],
            action_count=config["action_count"],
            output_count=config["output_count"],
        )
        combined = CandidateSystem([*system.machines.values(), target])
        classes = initial_behavioral_classes(combined)
        target_class = next(group for group in classes if "OUTSIDE" in group)
        if target_class != ("OUTSIDE",):
            rejection_counts["outside_behaviorally_in_family"] += 1
            continue
        outside = target
        outside_attempt = attempt
        break
    if outside is None or outside_attempt is None:
        raise RuntimeError(f"006a could not generate outside target {case_index}")

    policy_bytes = pretty_bytes(adaptive.to_dict())
    manifest = {
        "accepted_candidate_attempt": accepted_attempt,
        "candidate_sha256": {
            name: machine_hash(machine) for name, machine in sorted(system.machines.items())
        },
        "case_id": f"C{case_index:04d}",
        "oia_policy_sha256": sha256_bytes(policy_bytes),
        "oia_reachable_beliefs": adaptive.reachable_beliefs,
        "oia_root_action": adaptive.policy.action,
        "oia_worst_case_steps": adaptive.worst_case_steps,
        "outside_accepted_attempt": outside_attempt,
        "outside_sha256": machine_hash(outside),
        "rejection_counts": dict(sorted(rejection_counts.items())),
    }
    return system, outside, adaptive, manifest


def target_step(machine: MealyMachine, state: str, action: str) -> tuple[str, str]:
    transition = machine.step(state, action)
    return transition.output, transition.next_state


def classify_leaf(candidates: tuple[str, ...], target_name: str, target_kind: str) -> dict[str, Any]:
    if len(candidates) != 1:
        return {"status": "unresolved", "identified_candidate": None}
    identified = candidates[0]
    if target_kind == "in_family" and identified == target_name:
        status = "correct_candidate_identification"
    elif target_kind == "outside":
        status = "false_candidate_identification"
    else:
        status = "incorrect_candidate_identification"
    return {"status": status, "identified_candidate": identified}


def execute_adaptive(
    policy: PolicyNode,
    target: MealyMachine,
    target_kind: str,
    horizon: int,
) -> dict[str, Any]:
    state = target.initial_state
    node = policy
    actions: list[str] = []
    outputs: list[str] = []
    while len(actions) < horizon and not node.is_leaf:
        if node.action is None:
            raise RuntimeError("006a malformed OIA policy")
        action = node.action
        output, state = target_step(target, state, action)
        actions.append(action)
        outputs.append(output)
        child = node.branches.get(output)
        if child is None:
            return {
                "action_trace": actions,
                "identified_candidate": None,
                "output_trace": outputs,
                "status": "outside_model",
                "steps": len(actions),
            }
        node = child
    leaf = classify_leaf(node.candidates, target.name, target_kind) if node.is_leaf else {
        "status": "unresolved",
        "identified_candidate": None,
    }
    return {
        "action_trace": actions,
        "identified_candidate": leaf["identified_candidate"],
        "output_trace": outputs,
        "status": leaf["status"],
        "steps": len(actions),
    }


def greedy_action(system: CandidateSystem, belief: Belief) -> str:
    scored = []
    for action in system.actions:
        branches = system.step_belief(belief, action)
        sizes = tuple(len(branch) for branch in branches.values())
        scored.append((max(sizes), sum(size * size for size in sizes), action))
    return min(scored)[2]


def execute_belief_policy(
    system: CandidateSystem,
    target: MealyMachine,
    target_kind: str,
    horizon: int,
    choose_action: Callable[[CandidateSystem, Belief, int], str],
) -> dict[str, Any]:
    belief = system.initial_belief
    state = target.initial_state
    actions: list[str] = []
    outputs: list[str] = []
    for step_index in range(horizon):
        if len(belief) == 1:
            break
        action = choose_action(system, belief, step_index)
        output, state = target_step(target, state, action)
        actions.append(action)
        outputs.append(output)
        branches = system.step_belief(belief, action)
        if output not in branches:
            return {
                "action_trace": actions,
                "identified_candidate": None,
                "output_trace": outputs,
                "status": "outside_model",
                "steps": len(actions),
            }
        belief = branches[output]
    leaf = classify_leaf(belief_models(belief), target.name, target_kind)
    return {
        "action_trace": actions,
        "identified_candidate": leaf["identified_candidate"],
        "output_trace": outputs,
        "status": leaf["status"],
        "steps": len(actions),
    }


def record(
    case_id: str,
    target_kind: str,
    target_id: str,
    policy_name: str,
    trial: int,
    horizon: int,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "horizon": horizon,
        "policy": policy_name,
        "target_id": target_id,
        "target_kind": target_kind,
        "trial": trial,
        **outcome,
    }


def collect(config: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifests: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for case_index in range(config["case_count"]):
        system, outside, adaptive, manifest = generate_case(config, case_index)
        manifests.append(manifest)
        if adaptive.policy is None or adaptive.worst_case_steps is None:
            raise RuntimeError("006a accepted policy missing")
        horizon = adaptive.worst_case_steps
        targets = [
            ("in_family", name, machine)
            for name, machine in sorted(system.machines.items())
        ] + [("outside", "OUTSIDE", outside)]
        for target_kind, target_id, target in targets:
            records.append(
                record(
                    manifest["case_id"],
                    target_kind,
                    target_id,
                    "oia_adaptive",
                    0,
                    horizon,
                    execute_adaptive(adaptive.policy, target, target_kind, horizon),
                )
            )
            records.append(
                record(
                    manifest["case_id"],
                    target_kind,
                    target_id,
                    "greedy_one_step",
                    0,
                    horizon,
                    execute_belief_policy(
                        system,
                        target,
                        target_kind,
                        horizon,
                        lambda current_system, belief, _step: greedy_action(current_system, belief),
                    ),
                )
            )
            for trial in range(config["random_trials_per_target"]):
                rng = random.Random(
                    derived_seed(
                        config["master_seed"],
                        "random_policy",
                        manifest["case_id"],
                        target_kind,
                        target_id,
                        trial,
                    )
                )
                records.append(
                    record(
                        manifest["case_id"],
                        target_kind,
                        target_id,
                        "uniform_random",
                        trial,
                        horizon,
                        execute_belief_policy(
                            system,
                            target,
                            target_kind,
                            horizon,
                            lambda current_system, _belief, _step, generator=rng: generator.choice(
                                current_system.actions
                            ),
                        ),
                    )
                )

    aggregates: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for item in records:
        key = (item["policy"], item["target_kind"])
        aggregate = aggregates[key]
        aggregate["records"] += 1
        aggregate[f"status:{item['status']}"] += 1
        aggregate["total_steps"] += item["steps"]
    summary_rows = [
        {
            "policy": policy,
            "target_kind": target_kind,
            **dict(sorted(counts.items())),
        }
        for (policy, target_kind), counts in sorted(aggregates.items())
    ]
    record_lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records]
    result = {
        "audit_id": "OIA-1-TRACK-A-006a",
        "benchmark": config,
        "case_count": len(manifests),
        "case_manifest_sha256": sha256_bytes(pretty_bytes(manifests)),
        "claim_boundary": "Controlled deterministic simulation of within-frontier identification and outside-frontier detection under frozen finite candidate sets. This is not external validation, learned ontology formation, necessary revision, sealed transfer, or decision superiority.",
        "record_count": len(records),
        "records_jsonl_sha256": sha256_bytes(("\n".join(record_lines) + "\n").encode("utf-8")),
        "schema_version": 1,
        "summary": summary_rows,
    }
    return result, manifests, records


def add_zip_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100444 << 16
    archive.writestr(info, payload)


def write_outcome(destination: Path, config: dict[str, Any]) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    destination.mkdir(parents=True)
    result, manifests, records = collect(config)
    evidence_path = destination / "CONTROLLED_OPEN_WORLD_EVIDENCE.zip"
    record_bytes = (
        "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records)
        + "\n"
    ).encode("utf-8")
    with zipfile.ZipFile(evidence_path, "w") as archive:
        add_zip_bytes(archive, "CASE_MANIFEST.json", pretty_bytes(manifests))
        add_zip_bytes(archive, "RUN_RECORDS.jsonl", record_bytes)
    result["evidence_package"] = {
        "path": evidence_path.name,
        "sha256": sha256_file(evidence_path),
        "size_bytes": evidence_path.stat().st_size,
    }
    (destination / "CONTROLLED_OPEN_WORLD_RESULT.json").write_bytes(pretty_bytes(result))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--execute-frozen-outcome", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.preflight_only:
        print(json.dumps(preflight(), sort_keys=True))
        return
    if args.output is None:
        raise SystemExit("--output is required")
    if args.fixture:
        result = write_outcome(args.output.resolve(), fixture_config())
        print(json.dumps(result, sort_keys=True))
        return
    if not args.execute_frozen_outcome:
        raise SystemExit("refusing benchmark outcome generation without --execute-frozen-outcome")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    preflight()
    result = write_outcome(args.output.resolve(), benchmark_config(protocol))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
