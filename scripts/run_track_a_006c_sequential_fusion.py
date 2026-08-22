#!/usr/bin/env python3
"""Run the frozen Track A 006c resettable sequential-fusion diagnostic."""

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
PARENT_RUNNER_PATH = ROOT / "scripts" / "run_track_a_006b_reject_aware.py"
PARENT_RUNNER_SHA256 = "4e6d49ff091fc38c337d45800e5ede9e4576d39b3c1c0e7ac98a1a1fefbe1860"
AUDIT_ROOT = ROOT / "audits" / "track-a-006c"
PROTOCOL_PATH = AUDIT_ROOT / "SEQUENTIAL_FUSION_PROTOCOL.frozen.json"
BENCHMARK_MASTER_SEED = "oia-track-a-006c-heldout-v1"
FIXTURE_MASTER_SEED = "oia-track-a-006c-fixture-v1"


def load_parent() -> Any:
    spec = importlib.util.spec_from_file_location("track_a_006b_parent", PARENT_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned Track A 006b runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parent = load_parent()


def pretty_bytes(value: object) -> bytes:
    return parent.pretty_bytes(value)


def config(master_seed: str, case_count: int) -> dict[str, Any]:
    return {
        "master_seed": master_seed,
        "case_count": case_count,
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


def fixture_config() -> dict[str, Any]:
    return config(FIXTURE_MASTER_SEED, 3)


def benchmark_config(protocol: dict[str, Any]) -> dict[str, Any]:
    value = dict(protocol["benchmark"])
    if value != config(BENCHMARK_MASTER_SEED, 64):
        raise ValueError("006c held-out benchmark configuration changed")
    return value


def preflight() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status_at_freeze"] != "frozen_before_heldout_case_generation_or_target_execution":
        raise ValueError("006c prospective ordering changed")
    if benchmark_config(protocol)["master_seed"] == FIXTURE_MASTER_SEED:
        raise ValueError("006c benchmark and fixture seeds overlap")
    if parent.sha256_file(PARENT_RUNNER_PATH) != PARENT_RUNNER_SHA256:
        raise ValueError("006c pinned 006b parent runner changed")
    return {
        "audit_id": "OIA-1-TRACK-A-006c",
        "benchmark_cases_generated": 0,
        "benchmark_targets_executed": 0,
        "parent_runner_sha256": PARENT_RUNNER_SHA256,
        "pass": True,
        "status": "sequential_fusion_preflight_passed",
    }


def component_outcomes(
    target: Any,
    target_kind: str,
    closed: Any,
    reject: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        closed.policy is None
        or closed.worst_case_steps is None
        or reject.policy is None
        or reject.worst_case_steps is None
    ):
        raise RuntimeError("006c accepted policy missing")
    closed_outcome = parent.execute_policy(
        closed.policy,
        target,
        target_kind,
        closed.worst_case_steps,
        reject_aware=False,
    )
    reject_outcome = parent.execute_policy(
        reject.policy,
        target,
        target_kind,
        reject.worst_case_steps,
        reject_aware=True,
    )
    return closed_outcome, reject_outcome


def fuse(
    target_kind: str,
    target_id: str,
    closed: dict[str, Any],
    reject: dict[str, Any],
) -> dict[str, Any]:
    if closed["status"] == "outside_model":
        status = "outside_detected_closed"
        identified = None
        resets = 0
        actions = list(closed["action_trace"])
        outputs = list(closed["output_trace"])
        steps = closed["steps"]
    else:
        resets = 1
        actions = [*closed["action_trace"], "__reset__", *reject["action_trace"]]
        outputs = [*closed["output_trace"], "reset", *reject["output_trace"]]
        steps = closed["steps"] + reject["steps"]
        if reject["status"] in {"outside_model", "outside_reject"}:
            status = "outside_detected_reject"
            identified = None
        elif closed["identified_candidate"] != reject["identified_candidate"]:
            status = "outside_detected_disagreement"
            identified = None
        else:
            identified = closed["identified_candidate"]
            if target_kind == "in_family" and identified == target_id:
                status = "correct_candidate_identification"
            elif target_kind == "outside":
                status = "false_candidate_identification"
            else:
                status = "incorrect_candidate_identification"
    return {
        "action_trace": actions,
        "identified_candidate": identified,
        "output_trace": outputs,
        "reset_count": resets,
        "status": status,
        "steps": steps,
    }


def make_record(
    case_id: str,
    target_kind: str,
    target_id: str,
    policy: str,
    horizon: int,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "horizon": horizon,
        "policy": policy,
        "target_id": target_id,
        "target_kind": target_kind,
        "reset_count": 0,
        **outcome,
    }


def collect(
    run_config: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifests: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for case_index in range(run_config["case_count"]):
        base, _augmented, outside, closed, reject, manifest = parent.generate_case(
            run_config, case_index
        )
        manifests.append(manifest)
        if closed.worst_case_steps is None or reject.worst_case_steps is None:
            raise RuntimeError("006c accepted policy depth missing")
        targets = [
            ("in_family", name, machine)
            for name, machine in sorted(base.machines.items())
        ] + [("outside", "OUTSIDE", outside)]
        for target_kind, target_id, target in targets:
            closed_outcome, reject_outcome = component_outcomes(
                target, target_kind, closed, reject
            )
            records.append(
                make_record(
                    manifest["case_id"],
                    target_kind,
                    target_id,
                    "closed_identity_native",
                    closed.worst_case_steps,
                    closed_outcome,
                )
            )
            records.append(
                make_record(
                    manifest["case_id"],
                    target_kind,
                    target_id,
                    "reject_aware_native",
                    reject.worst_case_steps,
                    reject_outcome,
                )
            )
            records.append(
                make_record(
                    manifest["case_id"],
                    target_kind,
                    target_id,
                    "sequential_fusion",
                    closed.worst_case_steps + reject.worst_case_steps,
                    fuse(target_kind, target_id, closed_outcome, reject_outcome),
                )
            )

    aggregates: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for item in records:
        aggregate = aggregates[(item["policy"], item["target_kind"])]
        aggregate["records"] += 1
        aggregate[f"status:{item['status']}"] += 1
        aggregate["total_resets"] += item["reset_count"]
        aggregate["total_steps"] += item["steps"]
    summary = [
        {"policy": policy, "target_kind": kind, **dict(sorted(counts.items()))}
        for (policy, kind), counts in sorted(aggregates.items())
    ]
    lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records]
    result = {
        "audit_id": "OIA-1-TRACK-A-006c",
        "benchmark": run_config,
        "case_count": len(manifests),
        "case_manifest_sha256": parent.parent.sha256_bytes(pretty_bytes(manifests)),
        "claim_boundary": (
            "Controlled deterministic Track A diagnostic of a frozen resettable "
            "sequential fusion. This is not external validation, learned ontology "
            "formation, necessary revision, sealed transfer, population inference, "
            "real ARC evidence, or decision superiority."
        ),
        "record_count": len(records),
        "records_jsonl_sha256": parent.parent.sha256_bytes(
            ("\n".join(lines) + "\n").encode("utf-8")
        ),
        "schema_version": 1,
        "summary": summary,
    }
    return result, manifests, records


def write_outcome(destination: Path, run_config: dict[str, Any]) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    destination.mkdir(parents=True)
    result, manifests, records = collect(run_config)
    evidence_path = destination / "SEQUENTIAL_FUSION_EVIDENCE.zip"
    record_bytes = (
        "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records)
        + "\n"
    ).encode("utf-8")
    with zipfile.ZipFile(evidence_path, "w") as archive:
        parent.parent.add_zip_bytes(archive, "CASE_MANIFEST.json", pretty_bytes(manifests))
        parent.parent.add_zip_bytes(archive, "RUN_RECORDS.jsonl", record_bytes)
    result["evidence_package"] = {
        "path": evidence_path.name,
        "sha256": parent.sha256_file(evidence_path),
        "size_bytes": evidence_path.stat().st_size,
    }
    (destination / "SEQUENTIAL_FUSION_RESULT.json").write_bytes(pretty_bytes(result))
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
