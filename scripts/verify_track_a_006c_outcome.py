#!/usr/bin/env python3
"""Independently regenerate and verify the Track A 006c outcome."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-006c"
OUTCOME_ROOT = AUDIT_ROOT / "outcome"
EXPECTED_RESULT_SHA256 = "84764a578a26864ff45ecea2e86d4ae16f7d24ad365a809f3c15a83979a941f3"
EXPECTED_EVIDENCE_SHA256 = "bbe1df7f1925a1db503fde0909984c0372eb6e997b70c175127c5d21742f5111"
EXPECTED_PATHS = {
    "audits/track-a-006c/outcome/OUTCOME_REPORT.md",
    "audits/track-a-006c/outcome/SEQUENTIAL_FUSION_EVIDENCE.zip",
    "audits/track-a-006c/outcome/SEQUENTIAL_FUSION_RESULT.json",
    "scripts/verify_track_a_006c_outcome.py",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_runner() -> Any:
    path = ROOT / "scripts" / "run_track_a_006c_sequential_fusion.py"
    spec = importlib.util.spec_from_file_location("track_a_006c_runner_verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load 006c runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def summary_row(result: dict[str, Any], policy: str, kind: str) -> dict[str, Any]:
    return next(
        row
        for row in result["summary"]
        if row["policy"] == policy and row["target_kind"] == kind
    )


def grouped_records(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        key = (record["case_id"], record["target_id"])
        grouped[key][record["policy"]] = record
    if len(grouped) != 320 or any(len(methods) != 3 for methods in grouped.values()):
        raise ValueError("006c per-target record accounting changed")
    return grouped


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "SEQUENTIAL_FUSION_OUTCOME_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006c outcome checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006c outcome path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("006c outcome path set changed")

    result_path = OUTCOME_ROOT / "SEQUENTIAL_FUSION_RESULT.json"
    evidence_path = OUTCOME_ROOT / "SEQUENTIAL_FUSION_EVIDENCE.zip"
    if sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise ValueError("006c result changed")
    if sha256(evidence_path) != EXPECTED_EVIDENCE_SHA256:
        raise ValueError("006c evidence changed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["case_count"] != 64 or result["record_count"] != 960:
        raise ValueError("006c outcome accounting changed")
    if result["case_manifest_sha256"] != "06e29472c77c5f1d0542b6eeb6843bb0a802d8198fdc43bb4cfd8e9a389c7bc7":
        raise ValueError("006c case manifest changed")
    if result["records_jsonl_sha256"] != "b28feda465b923979821297524d174a916684d741bd298f9062df6b83776e90f":
        raise ValueError("006c record stream changed")
    if result["evidence_package"] != {
        "path": "SEQUENTIAL_FUSION_EVIDENCE.zip",
        "sha256": EXPECTED_EVIDENCE_SHA256,
        "size_bytes": 34646,
    }:
        raise ValueError("006c evidence provenance changed")

    with zipfile.ZipFile(evidence_path) as archive:
        infos = archive.infolist()
        if {info.filename for info in infos} != {"CASE_MANIFEST.json", "RUN_RECORDS.jsonl"}:
            raise ValueError("006c evidence paths changed")
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("006c duplicate evidence paths")
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir():
                raise ValueError(f"unsafe 006c evidence path: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0) or (info.external_attr >> 16) != 0o100444:
                raise ValueError(f"006c nondeterministic ZIP metadata: {info.filename}")
        evidence_manifests = json.loads(archive.read("CASE_MANIFEST.json"))
        evidence_records = [
            json.loads(line) for line in archive.read("RUN_RECORDS.jsonl").splitlines()
        ]

    runner = load_runner()
    protocol = json.loads(
        (AUDIT_ROOT / "SEQUENTIAL_FUSION_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    run_config = runner.benchmark_config(protocol)
    regenerated, manifests, records = runner.collect(run_config)
    if manifests != evidence_manifests or records != evidence_records:
        raise ValueError("006c regenerated evidence differs")
    for field in (
        "audit_id",
        "benchmark",
        "case_count",
        "case_manifest_sha256",
        "claim_boundary",
        "record_count",
        "records_jsonl_sha256",
        "schema_version",
        "summary",
    ):
        if result[field] != regenerated[field]:
            raise ValueError(f"006c regenerated result differs: {field}")

    for case_index, expected_manifest in enumerate(manifests):
        base, augmented, outside, closed, reject, manifest = runner.parent.generate_case(
            run_config, case_index
        )
        if manifest != expected_manifest:
            raise ValueError(f"006c case {case_index} regeneration changed")
        if not runner.parent.globally_distinct([*augmented.machines.values(), outside]):
            raise ValueError(f"006c case {case_index} target is not globally distinct")
        if (
            runner.parent.verify_policy_witness(base, closed.policy)
            != closed.worst_case_steps
        ):
            raise ValueError(f"006c case {case_index} closed witness failed")
        if (
            runner.parent.verify_policy_witness(
                augmented, reject.policy, runner.parent.reject_aware_terminal
            )
            != reject.worst_case_steps
        ):
            raise ValueError(f"006c case {case_index} reject witness failed")

    expected_rows = {
        ("closed_identity_native", "in_family"): (256, 700, 0, {"status:correct_candidate_identification": 256}),
        ("closed_identity_native", "outside"): (64, 160, 0, {"status:false_candidate_identification": 47, "status:outside_model": 17}),
        ("reject_aware_native", "in_family"): (256, 771, 0, {"status:correct_candidate_identification": 256}),
        ("reject_aware_native", "outside"): (64, 177, 0, {"status:false_candidate_identification": 30, "status:outside_model": 15, "status:outside_reject": 19}),
        ("sequential_fusion", "in_family"): (256, 1471, 256, {"status:correct_candidate_identification": 256}),
        ("sequential_fusion", "outside"): (64, 289, 47, {"status:false_candidate_identification": 21, "status:outside_detected_closed": 17, "status:outside_detected_disagreement": 6, "status:outside_detected_reject": 20}),
    }
    for (policy, kind), (count, steps, resets, statuses) in expected_rows.items():
        expected = {
            "policy": policy,
            "records": count,
            "target_kind": kind,
            "total_resets": resets,
            "total_steps": steps,
            **statuses,
        }
        if summary_row(result, policy, kind) != expected:
            raise ValueError(f"006c summary row changed: {policy}/{kind}")

    groups = grouped_records(records)
    pairs: Counter[tuple[str, str, bool, str]] = Counter()
    for methods in groups.values():
        closed = methods["closed_identity_native"]
        reject = methods["reject_aware_native"]
        fusion = methods["sequential_fusion"]
        if closed["status"] == "outside_model":
            if (
                fusion["status"] != "outside_detected_closed"
                or fusion["reset_count"] != 0
                or fusion["steps"] != closed["steps"]
                or "__reset__" in fusion["action_trace"]
            ):
                raise ValueError("006c failed to preserve a closed novelty result")
        else:
            if (
                fusion["reset_count"] != 1
                or fusion["steps"] != closed["steps"] + reject["steps"]
                or fusion["action_trace"].count("__reset__") != 1
                or fusion["output_trace"].count("reset") != 1
            ):
                raise ValueError("006c reset or step accounting changed")
        if closed["target_kind"] == "outside":
            pairs[
                (
                    closed["status"],
                    reject["status"],
                    closed["identified_candidate"] == reject["identified_candidate"],
                    fusion["status"],
                )
            ] += 1
    expected_pairs = Counter(
        {
            ("false_candidate_identification", "false_candidate_identification", True, "false_candidate_identification"): 21,
            ("false_candidate_identification", "false_candidate_identification", False, "outside_detected_disagreement"): 6,
            ("false_candidate_identification", "outside_model", False, "outside_detected_reject"): 8,
            ("false_candidate_identification", "outside_reject", False, "outside_detected_reject"): 12,
            ("outside_model", "false_candidate_identification", False, "outside_detected_closed"): 3,
            ("outside_model", "outside_model", True, "outside_detected_closed"): 7,
            ("outside_model", "outside_reject", True, "outside_detected_closed"): 7,
        }
    )
    if pairs != expected_pairs:
        raise ValueError("006c paired component/fusion counts changed")

    if Counter(item["closed_worst_case_steps"] for item in manifests) != Counter({3: 60, 4: 4}):
        raise ValueError("006c closed depth distribution changed")
    if Counter(item["reject_aware_worst_case_steps"] for item in manifests) != Counter({3: 47, 4: 17}):
        raise ValueError("006c reject depth distribution changed")
    if any(
        item["accepted_base_attempt"]
        or item["accepted_sentinel_attempt"]
        or item["accepted_outside_attempt"]
        or item["rejection_counts"]
        for item in manifests
    ):
        raise ValueError("006c generation attempt accounting changed")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006c",
                "fusion_in_family_correct": 256,
                "fusion_outside_detected": 43,
                "fusion_outside_false_identification": 21,
                "pass": True,
                "record_count": len(records),
                "status": "sequential_fusion_outcome_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
