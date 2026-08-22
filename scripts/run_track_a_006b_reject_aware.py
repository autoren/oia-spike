#!/usr/bin/env python3
"""Run the frozen Track A 006b reject-aware controlled diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PARENT_RUNNER_PATH = ROOT / "scripts" / "run_track_a_006a_controlled_open_world.py"
PARENT_RUNNER_SHA256 = "ffa2c2916662225e06041a4346e8a255953a1addb62b480d412637f8851d1231"
AUDIT_ROOT = ROOT / "audits" / "track-a-006b"
PROTOCOL_PATH = AUDIT_ROOT / "REJECT_AWARE_PROTOCOL.frozen.json"
BENCHMARK_MASTER_SEED = "oia-track-a-006b-heldout-v1"
FIXTURE_MASTER_SEED = "oia-track-a-006b-fixture-v1"


def load_parent() -> Any:
    spec = importlib.util.spec_from_file_location("track_a_006a_parent", PARENT_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned Track A 006a runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parent = load_parent()
CandidateSystem = parent.CandidateSystem
MealyMachine = parent.MealyMachine
PolicyNode = parent.PolicyNode
belief_models = parent.belief_models
initial_behavioral_classes = parent.initial_behavioral_classes
synthesize_adaptive_policy = parent.synthesize_adaptive_policy
from ontology_auditor import verify_policy_witness  # noqa: E402


def sha256_file(path: Path) -> str:
    return parent.sha256_file(path)


def pretty_bytes(value: object) -> bytes:
    return parent.pretty_bytes(value)


def benchmark_config(protocol: dict[str, Any]) -> dict[str, Any]:
    config = dict(protocol["benchmark"])
    if config["master_seed"] != BENCHMARK_MASTER_SEED:
        raise ValueError("006b held-out benchmark seed changed")
    return config


def fixture_config() -> dict[str, Any]:
    return {
        "master_seed": FIXTURE_MASTER_SEED,
        "case_count": 3,
        "base_candidate_count": 4,
        "sentinel_count": 2,
        "state_count": 3,
        "action_count": 3,
        "output_count": 3,
        "minimum_closed_depth": 2,
        "maximum_closed_depth": 6,
        "maximum_reject_aware_depth": 8,
        "maximum_generation_attempts_per_stage": 2000,
        "max_beliefs": 100000,
    }


def preflight() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status_at_freeze"] != "frozen_before_heldout_case_generation_or_target_execution":
        raise ValueError("006b prospective ordering changed")
    if benchmark_config(protocol)["master_seed"] == FIXTURE_MASTER_SEED:
        raise ValueError("006b benchmark and fixture seeds overlap")
    if sha256_file(PARENT_RUNNER_PATH) != PARENT_RUNNER_SHA256:
        raise ValueError("006b pinned 006a parent runner changed")
    return {
        "audit_id": "OIA-1-TRACK-A-006b",
        "benchmark_cases_generated": 0,
        "benchmark_targets_executed": 0,
        "parent_runner_sha256": PARENT_RUNNER_SHA256,
        "pass": True,
        "status": "reject_aware_preflight_passed",
    }


def base_names(belief: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(name for name in belief_models(belief) if name.startswith("H"))


def sentinel_names(belief: tuple[Any, ...]) -> tuple[str, ...]:
    return tuple(name for name in belief_models(belief) if name.startswith("S"))


def reject_aware_terminal(belief: tuple[Any, ...]) -> bool:
    bases = base_names(belief)
    sentinels = sentinel_names(belief)
    return not bases or (len(bases) == 1 and not sentinels)


def reject_aware_description(belief: tuple[Any, ...]) -> str:
    bases = base_names(belief)
    sentinels = sentinel_names(belief)
    if not bases:
        return f"reject base frontier; surviving sentinels: {', '.join(sentinels)}"
    if len(bases) == 1 and not sentinels:
        return f"identified base candidate {bases[0]}"
    return "nonterminal reject-aware belief"


def globally_distinct(machines: list[MealyMachine]) -> bool:
    return len(initial_behavioral_classes(CandidateSystem(machines))) == len(machines)


def generated_machine(
    name: str,
    config: dict[str, Any],
    case_index: int,
    stage: str,
    attempt: int,
    member: int,
) -> MealyMachine:
    return parent.random_delayed_machine(
        name,
        parent.derived_seed(
            config["master_seed"], stage, case_index, attempt, member
        ),
        state_count=config["state_count"],
        action_count=config["action_count"],
        output_count=config["output_count"],
    )


def generate_case(
    config: dict[str, Any], case_index: int
) -> tuple[CandidateSystem, CandidateSystem, MealyMachine, Any, Any, dict[str, Any]]:
    rejection_counts: Counter[str] = Counter()
    base_system = None
    closed = None
    base_attempt = None
    for attempt in range(config["maximum_generation_attempts_per_stage"]):
        bases = [
            generated_machine(f"H{index}", config, case_index, "base", attempt, index)
            for index in range(config["base_candidate_count"])
        ]
        if not globally_distinct(bases):
            rejection_counts["base_behavioral_equivalence"] += 1
            continue
        trial_system = CandidateSystem(bases)
        trial_closed = synthesize_adaptive_policy(
            trial_system, max_beliefs=config["max_beliefs"]
        )
        if trial_closed.status != "solved" or not trial_closed.exact or trial_closed.policy is None:
            rejection_counts[f"closed_{trial_closed.status}"] += 1
            continue
        depth = trial_closed.worst_case_steps
        if depth is None or not config["minimum_closed_depth"] <= depth <= config["maximum_closed_depth"]:
            rejection_counts["closed_depth_out_of_range"] += 1
            continue
        base_system = trial_system
        closed = trial_closed
        base_attempt = attempt
        break
    if base_system is None or closed is None or base_attempt is None:
        raise RuntimeError(f"006b could not generate base case {case_index}")

    augmented_system = None
    reject_aware = None
    sentinel_attempt = None
    for attempt in range(config["maximum_generation_attempts_per_stage"]):
        sentinels = [
            generated_machine(f"S{index}", config, case_index, "sentinel", attempt, index)
            for index in range(config["sentinel_count"])
        ]
        combined = [*base_system.machines.values(), *sentinels]
        if not globally_distinct(combined):
            rejection_counts["sentinel_behavioral_equivalence"] += 1
            continue
        trial_system = CandidateSystem(combined)
        trial_reject = synthesize_adaptive_policy(
            trial_system,
            reject_aware_terminal,
            reject_aware_description,
            max_beliefs=config["max_beliefs"],
        )
        if trial_reject.status != "solved" or not trial_reject.exact or trial_reject.policy is None:
            rejection_counts[f"reject_aware_{trial_reject.status}"] += 1
            continue
        depth = trial_reject.worst_case_steps
        if depth is None or depth > config["maximum_reject_aware_depth"]:
            rejection_counts["reject_aware_depth_out_of_range"] += 1
            continue
        augmented_system = trial_system
        reject_aware = trial_reject
        sentinel_attempt = attempt
        break
    if augmented_system is None or reject_aware is None or sentinel_attempt is None:
        raise RuntimeError(f"006b could not generate sentinel policy {case_index}")

    outside = None
    outside_attempt = None
    for attempt in range(config["maximum_generation_attempts_per_stage"]):
        target = generated_machine("OUTSIDE", config, case_index, "outside", attempt, 0)
        if not globally_distinct([*augmented_system.machines.values(), target]):
            rejection_counts["outside_behaviorally_in_augmented_family"] += 1
            continue
        outside = target
        outside_attempt = attempt
        break
    if outside is None or outside_attempt is None:
        raise RuntimeError(f"006b could not generate held-out target {case_index}")

    if closed.policy is None or reject_aware.policy is None:
        raise RuntimeError("006b accepted policy missing")
    manifest = {
        "accepted_base_attempt": base_attempt,
        "accepted_outside_attempt": outside_attempt,
        "accepted_sentinel_attempt": sentinel_attempt,
        "base_candidate_sha256": {
            name: parent.machine_hash(machine)
            for name, machine in sorted(base_system.machines.items())
        },
        "case_id": f"C{case_index:04d}",
        "closed_policy_sha256": parent.sha256_bytes(pretty_bytes(closed.to_dict())),
        "closed_reachable_beliefs": closed.reachable_beliefs,
        "closed_root_action": closed.policy.action,
        "closed_worst_case_steps": closed.worst_case_steps,
        "outside_sha256": parent.machine_hash(outside),
        "reject_aware_policy_sha256": parent.sha256_bytes(
            pretty_bytes(reject_aware.to_dict())
        ),
        "reject_aware_reachable_beliefs": reject_aware.reachable_beliefs,
        "reject_aware_root_action": reject_aware.policy.action,
        "reject_aware_worst_case_steps": reject_aware.worst_case_steps,
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "sentinel_sha256": {
            name: parent.machine_hash(machine)
            for name, machine in sorted(augmented_system.machines.items())
            if name.startswith("S")
        },
    }
    return base_system, augmented_system, outside, closed, reject_aware, manifest


def classify_reject_aware_leaf(
    candidates: tuple[str, ...], target_name: str, target_kind: str
) -> dict[str, Any]:
    bases = tuple(name for name in candidates if name.startswith("H"))
    if not bases:
        status = "outside_reject" if target_kind == "outside" else "incorrect_reject"
        return {"status": status, "identified_candidate": None}
    if len(bases) != 1 or len(candidates) != 1:
        return {"status": "unresolved", "identified_candidate": None}
    identified = bases[0]
    if target_kind == "in_family" and identified == target_name:
        status = "correct_candidate_identification"
    elif target_kind == "outside":
        status = "false_candidate_identification"
    else:
        status = "incorrect_candidate_identification"
    return {"status": status, "identified_candidate": identified}


def execute_policy(
    policy: PolicyNode,
    target: MealyMachine,
    target_kind: str,
    horizon: int,
    *,
    reject_aware: bool,
) -> dict[str, Any]:
    state = target.initial_state
    node = policy
    actions: list[str] = []
    outputs: list[str] = []
    while len(actions) < horizon and not node.is_leaf:
        if node.action is None:
            raise RuntimeError("006b malformed policy")
        action = node.action
        output, state = parent.target_step(target, state, action)
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
    if not node.is_leaf:
        leaf = {"status": "unresolved", "identified_candidate": None}
    elif reject_aware:
        leaf = classify_reject_aware_leaf(node.candidates, target.name, target_kind)
    else:
        leaf = parent.classify_leaf(node.candidates, target.name, target_kind)
    return {
        "action_trace": actions,
        "identified_candidate": leaf["identified_candidate"],
        "output_trace": outputs,
        "status": leaf["status"],
        "steps": len(actions),
    }


def make_record(
    case_id: str,
    target_kind: str,
    target_id: str,
    policy_name: str,
    horizon: int,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "horizon": horizon,
        "policy": policy_name,
        "target_id": target_id,
        "target_kind": target_kind,
        **outcome,
    }


def collect(
    config: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifests: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for case_index in range(config["case_count"]):
        base, _augmented, outside, closed, reject, manifest = generate_case(
            config, case_index
        )
        manifests.append(manifest)
        if (
            closed.policy is None
            or closed.worst_case_steps is None
            or reject.policy is None
            or reject.worst_case_steps is None
        ):
            raise RuntimeError("006b accepted policy missing")
        targets = [
            ("in_family", name, machine)
            for name, machine in sorted(base.machines.items())
        ] + [("outside", "OUTSIDE", outside)]
        for target_kind, target_id, target in targets:
            executions = (
                (
                    "closed_identity_native",
                    closed.policy,
                    closed.worst_case_steps,
                    False,
                ),
                (
                    "reject_aware_native",
                    reject.policy,
                    reject.worst_case_steps,
                    True,
                ),
                (
                    "reject_aware_equal_closed_horizon",
                    reject.policy,
                    closed.worst_case_steps,
                    True,
                ),
            )
            for policy_name, policy, horizon, is_reject_aware in executions:
                records.append(
                    make_record(
                        manifest["case_id"],
                        target_kind,
                        target_id,
                        policy_name,
                        horizon,
                        execute_policy(
                            policy,
                            target,
                            target_kind,
                            horizon,
                            reject_aware=is_reject_aware,
                        ),
                    )
                )

    aggregates: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for item in records:
        aggregate = aggregates[(item["policy"], item["target_kind"])]
        aggregate["records"] += 1
        aggregate[f"status:{item['status']}"] += 1
        aggregate["total_steps"] += item["steps"]
    summary = [
        {"policy": policy, "target_kind": target_kind, **dict(sorted(counts.items()))}
        for (policy, target_kind), counts in sorted(aggregates.items())
    ]
    record_lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records]
    result = {
        "audit_id": "OIA-1-TRACK-A-006b",
        "benchmark": config,
        "case_count": len(manifests),
        "case_manifest_sha256": parent.sha256_bytes(pretty_bytes(manifests)),
        "claim_boundary": (
            "Controlled deterministic Track A comparison of a frozen reject-aware "
            "sentinel policy with the closed identity policy. This is not external "
            "validation, learned ontology formation, necessary revision, sealed "
            "transfer, population inference, or decision superiority."
        ),
        "record_count": len(records),
        "records_jsonl_sha256": parent.sha256_bytes(
            ("\n".join(record_lines) + "\n").encode("utf-8")
        ),
        "schema_version": 1,
        "summary": summary,
    }
    return result, manifests, records


def write_outcome(destination: Path, config: dict[str, Any]) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    destination.mkdir(parents=True)
    result, manifests, records = collect(config)
    evidence_path = destination / "REJECT_AWARE_EVIDENCE.zip"
    record_bytes = (
        "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records)
        + "\n"
    ).encode("utf-8")
    with zipfile.ZipFile(evidence_path, "w") as archive:
        parent.add_zip_bytes(archive, "CASE_MANIFEST.json", pretty_bytes(manifests))
        parent.add_zip_bytes(archive, "RUN_RECORDS.jsonl", record_bytes)
    result["evidence_package"] = {
        "path": evidence_path.name,
        "sha256": sha256_file(evidence_path),
        "size_bytes": evidence_path.stat().st_size,
    }
    (destination / "REJECT_AWARE_RESULT.json").write_bytes(pretty_bytes(result))
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
        print(json.dumps(write_outcome(args.output.resolve(), fixture_config()), sort_keys=True))
        return
    if not args.execute_frozen_outcome:
        raise SystemExit("refusing held-out generation without --execute-frozen-outcome")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    preflight()
    print(
        json.dumps(
            write_outcome(args.output.resolve(), benchmark_config(protocol)),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
