#!/usr/bin/env python3
"""Independently regenerate and verify the Track A 006b outcome."""

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
AUDIT_ROOT = ROOT / "audits" / "track-a-006b"
OUTCOME_ROOT = AUDIT_ROOT / "outcome"
EXPECTED_RESULT_SHA256 = "9658409934ff31b3ca06cfd82880dab61508cbce17feff38547ed4760fa99feb"
EXPECTED_EVIDENCE_SHA256 = "c49fe7cc4212b70c6bba9c050295915209c16c1e3ad4cfb4bbb4244b177541c7"
EXPECTED_OUTCOME_PATHS = {
    "audits/track-a-006b/outcome/OUTCOME_REPORT.md",
    "audits/track-a-006b/outcome/REJECT_AWARE_EVIDENCE.zip",
    "audits/track-a-006b/outcome/REJECT_AWARE_RESULT.json",
    "scripts/verify_track_a_006b_outcome.py",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_runner() -> Any:
    path = ROOT / "scripts" / "run_track_a_006b_reject_aware.py"
    spec = importlib.util.spec_from_file_location("track_a_006b_runner_verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load 006b runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def summary_row(result: dict[str, Any], policy: str, target_kind: str) -> dict[str, Any]:
    return next(
        row
        for row in result["summary"]
        if row["policy"] == policy and row["target_kind"] == target_kind
    )


def paired_counts(records: list[dict[str, Any]], second_policy: str) -> Counter[tuple[str, str]]:
    by_case: dict[str, dict[str, str]] = defaultdict(dict)
    for record in records:
        if record["target_kind"] != "outside":
            continue
        if record["policy"] in {"closed_identity_native", second_policy}:
            by_case[record["case_id"]][record["policy"]] = record["status"]
    if len(by_case) != 64 or any(len(values) != 2 for values in by_case.values()):
        raise ValueError("006b paired outside record accounting changed")
    return Counter(
        (values["closed_identity_native"], values[second_policy])
        for values in by_case.values()
    )


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "REJECT_AWARE_OUTCOME_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006b outcome checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006b outcome path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_OUTCOME_PATHS:
        raise ValueError("006b outcome path set changed")

    result_path = OUTCOME_ROOT / "REJECT_AWARE_RESULT.json"
    evidence_path = OUTCOME_ROOT / "REJECT_AWARE_EVIDENCE.zip"
    if sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise ValueError("006b result changed")
    if sha256(evidence_path) != EXPECTED_EVIDENCE_SHA256:
        raise ValueError("006b evidence changed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["case_count"] != 64 or result["record_count"] != 960:
        raise ValueError("006b outcome accounting changed")
    if result["case_manifest_sha256"] != "a8f56e7b15482d7091d8d6869462027ca050add066404b288c2f490b7454cef6":
        raise ValueError("006b case manifest changed")
    if result["records_jsonl_sha256"] != "d99b32fe5c4fd9ad61d048eef52e20eec81a8452f1e558ee1217953da2211af2":
        raise ValueError("006b record stream changed")
    if result["evidence_package"] != {
        "path": "REJECT_AWARE_EVIDENCE.zip",
        "sha256": EXPECTED_EVIDENCE_SHA256,
        "size_bytes": 32122,
    }:
        raise ValueError("006b evidence provenance changed")

    with zipfile.ZipFile(evidence_path) as archive:
        infos = archive.infolist()
        if {info.filename for info in infos} != {"CASE_MANIFEST.json", "RUN_RECORDS.jsonl"}:
            raise ValueError("006b evidence paths changed")
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("006b duplicate evidence paths")
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir():
                raise ValueError(f"unsafe 006b evidence path: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0) or (info.external_attr >> 16) != 0o100444:
                raise ValueError(f"006b nondeterministic ZIP metadata: {info.filename}")
        evidence_manifests = json.loads(archive.read("CASE_MANIFEST.json"))
        evidence_records = [
            json.loads(line) for line in archive.read("RUN_RECORDS.jsonl").splitlines()
        ]

    runner = load_runner()
    protocol = json.loads(
        (AUDIT_ROOT / "REJECT_AWARE_PROTOCOL.frozen.json").read_text(encoding="utf-8")
    )
    regenerated, manifests, records = runner.collect(runner.benchmark_config(protocol))
    if manifests != evidence_manifests or records != evidence_records:
        raise ValueError("006b regenerated evidence differs")
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
            raise ValueError(f"006b regenerated result differs: {field}")

    for case_index, expected_manifest in enumerate(evidence_manifests):
        base, augmented, outside, closed, reject, manifest = runner.generate_case(
            runner.benchmark_config(protocol), case_index
        )
        if manifest != expected_manifest:
            raise ValueError(f"006b case {case_index} regeneration changed")
        if not runner.globally_distinct([*augmented.machines.values(), outside]):
            raise ValueError(f"006b case {case_index} target is not globally distinct")
        if runner.verify_policy_witness(base, closed.policy) != closed.worst_case_steps:
            raise ValueError(f"006b case {case_index} closed policy witness failed")
        if (
            runner.verify_policy_witness(
                augmented, reject.policy, runner.reject_aware_terminal
            )
            != reject.worst_case_steps
        ):
            raise ValueError(f"006b case {case_index} reject policy witness failed")

    closed_in = summary_row(result, "closed_identity_native", "in_family")
    reject_in = summary_row(result, "reject_aware_native", "in_family")
    equal_in = summary_row(result, "reject_aware_equal_closed_horizon", "in_family")
    closed_out = summary_row(result, "closed_identity_native", "outside")
    reject_out = summary_row(result, "reject_aware_native", "outside")
    equal_out = summary_row(result, "reject_aware_equal_closed_horizon", "outside")
    if closed_in != {
        "policy": "closed_identity_native",
        "records": 256,
        "status:correct_candidate_identification": 256,
        "target_kind": "in_family",
        "total_steps": 699,
    }:
        raise ValueError("006b closed in-family soundness changed")
    if reject_in != {
        "policy": "reject_aware_native",
        "records": 256,
        "status:correct_candidate_identification": 256,
        "target_kind": "in_family",
        "total_steps": 777,
    }:
        raise ValueError("006b reject-aware in-family soundness changed")
    if equal_in != {
        "policy": "reject_aware_equal_closed_horizon",
        "records": 256,
        "status:correct_candidate_identification": 222,
        "status:unresolved": 34,
        "target_kind": "in_family",
        "total_steps": 743,
    }:
        raise ValueError("006b equal-horizon in-family counts changed")
    if closed_out != {
        "policy": "closed_identity_native",
        "records": 64,
        "status:false_candidate_identification": 48,
        "status:outside_model": 16,
        "target_kind": "outside",
        "total_steps": 168,
    }:
        raise ValueError("006b closed outside counts changed")
    if reject_out != {
        "policy": "reject_aware_native",
        "records": 64,
        "status:false_candidate_identification": 35,
        "status:outside_model": 14,
        "status:outside_reject": 15,
        "target_kind": "outside",
        "total_steps": 185,
    }:
        raise ValueError("006b reject-aware outside counts changed")
    if equal_out != {
        "policy": "reject_aware_equal_closed_horizon",
        "records": 64,
        "status:false_candidate_identification": 32,
        "status:outside_model": 13,
        "status:outside_reject": 13,
        "status:unresolved": 6,
        "target_kind": "outside",
        "total_steps": 179,
    }:
        raise ValueError("006b equal-horizon outside counts changed")

    false_id = "false_candidate_identification"
    outside_model = "outside_model"
    outside_reject = "outside_reject"
    expected_native = Counter(
        {
            (false_id, false_id): 28,
            (false_id, outside_model): 7,
            (false_id, outside_reject): 13,
            (outside_model, false_id): 7,
            (outside_model, outside_model): 7,
            (outside_model, outside_reject): 2,
        }
    )
    if paired_counts(records, "reject_aware_native") != expected_native:
        raise ValueError("006b native paired counts changed")

    closed_depths = Counter(item["closed_worst_case_steps"] for item in manifests)
    reject_depths = Counter(item["reject_aware_worst_case_steps"] for item in manifests)
    depth_pairs = Counter(
        (item["closed_worst_case_steps"], item["reject_aware_worst_case_steps"])
        for item in manifests
    )
    if closed_depths != Counter({3: 62, 4: 2}):
        raise ValueError("006b closed depth distribution changed")
    if reject_depths != Counter({3: 45, 4: 19}):
        raise ValueError("006b reject-aware depth distribution changed")
    if depth_pairs != Counter({(3, 3): 45, (3, 4): 17, (4, 4): 2}):
        raise ValueError("006b paired depth distribution changed")
    rejections: Counter[str] = Counter()
    for manifest in manifests:
        rejections.update(manifest["rejection_counts"])
    if rejections != Counter(
        {"base_behavioral_equivalence": 2, "sentinel_behavioral_equivalence": 1}
    ):
        raise ValueError("006b generation rejection accounting changed")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006b",
                "closed_outside_detected": 16,
                "native_in_family_correct": 256,
                "pass": True,
                "record_count": len(records),
                "reject_aware_outside_detected": 29,
                "status": "reject_aware_outcome_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
