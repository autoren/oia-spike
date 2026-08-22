#!/usr/bin/env python3
"""Independently regenerate and verify the Track A 006a outcome package."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-006a"
OUTCOME_ROOT = AUDIT_ROOT / "outcome"
EXPECTED_RESULT_SHA256 = "80cdcff14d6081f79c68894304116bc6d3b47fb8891b05fc00499eb7c57ccc74"
EXPECTED_EVIDENCE_SHA256 = "57b18c6a17e6d879b13e08a8fcad9e942f17672d813eb152e707a50db397efdb"
EXPECTED_OUTCOME_PATHS = {
    "audits/track-a-006a/outcome/CONTROLLED_OPEN_WORLD_EVIDENCE.zip",
    "audits/track-a-006a/outcome/CONTROLLED_OPEN_WORLD_RESULT.json",
    "audits/track-a-006a/outcome/OUTCOME_REPORT.md",
    "scripts/verify_track_a_006a_outcome.py",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_runner() -> Any:
    path = ROOT / "scripts/run_track_a_006a_controlled_open_world.py"
    spec = importlib.util.spec_from_file_location("track_a_006a_runner_verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load 006a runner")
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


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "CONTROLLED_OPEN_WORLD_OUTCOME_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006a outcome checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006a outcome path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_OUTCOME_PATHS:
        raise ValueError("006a outcome path set changed")

    result_path = OUTCOME_ROOT / "CONTROLLED_OPEN_WORLD_RESULT.json"
    evidence_path = OUTCOME_ROOT / "CONTROLLED_OPEN_WORLD_EVIDENCE.zip"
    if sha256(result_path) != EXPECTED_RESULT_SHA256:
        raise ValueError("006a result changed")
    if sha256(evidence_path) != EXPECTED_EVIDENCE_SHA256:
        raise ValueError("006a evidence changed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["record_count"] != 10880 or result["case_count"] != 64:
        raise ValueError("006a outcome accounting changed")
    if result["evidence_package"] != {
        "path": "CONTROLLED_OPEN_WORLD_EVIDENCE.zip",
        "sha256": EXPECTED_EVIDENCE_SHA256,
        "size_bytes": 92533,
    }:
        raise ValueError("006a evidence provenance changed")

    with zipfile.ZipFile(evidence_path) as archive:
        infos = archive.infolist()
        if {info.filename for info in infos} != {"CASE_MANIFEST.json", "RUN_RECORDS.jsonl"}:
            raise ValueError("006a evidence paths changed")
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("006a duplicate evidence paths")
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir():
                raise ValueError(f"unsafe 006a evidence path: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0) or (info.external_attr >> 16) != 0o100444:
                raise ValueError(f"006a nondeterministic ZIP metadata: {info.filename}")
        evidence_manifests = json.loads(archive.read("CASE_MANIFEST.json"))
        evidence_records = [
            json.loads(line) for line in archive.read("RUN_RECORDS.jsonl").splitlines()
        ]

    runner = load_runner()
    protocol = json.loads(
        (AUDIT_ROOT / "CONTROLLED_OPEN_WORLD_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    regenerated, manifests, records = runner.collect(runner.benchmark_config(protocol))
    if manifests != evidence_manifests or records != evidence_records:
        raise ValueError("006a regenerated evidence differs")
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
            raise ValueError(f"006a regenerated result differs: {field}")

    oia_in = summary_row(result, "oia_adaptive", "in_family")
    oia_out = summary_row(result, "oia_adaptive", "outside")
    if oia_in.get("status:correct_candidate_identification") != 256 or oia_in["records"] != 256:
        raise ValueError("006a in-family soundness failed")
    if (
        oia_out["records"] != 64
        or oia_out.get("status:outside_model") != 17
        or oia_out.get("status:false_candidate_identification") != 47
    ):
        raise ValueError("006a primary outside counts changed")
    if {manifest["oia_worst_case_steps"] for manifest in manifests} != {3}:
        raise ValueError("006a OIA depth distribution changed")
    rejection_totals: dict[str, int] = {}
    for manifest in manifests:
        for reason, count in manifest["rejection_counts"].items():
            rejection_totals[reason] = rejection_totals.get(reason, 0) + count
    if rejection_totals != {
        "candidate_behavioral_equivalence": 1,
        "outside_behaviorally_in_family": 1,
    }:
        raise ValueError("006a generation rejection accounting changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006a",
                "in_family_correct": 256,
                "outside_detected": 17,
                "outside_false_identification": 47,
                "pass": True,
                "record_count": len(records),
                "status": "controlled_open_world_outcome_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
