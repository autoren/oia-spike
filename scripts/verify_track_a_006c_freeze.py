#!/usr/bin/env python3
"""Verify the pre-outcome Track A 006c sequential-fusion freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-006c"
EXPECTED_PATHS = {
    "README.md",
    "audits/track-a-006c/OPENED_SEQUENTIAL_DEVELOPMENT.json",
    "audits/track-a-006c/README.md",
    "audits/track-a-006c/SEQUENTIAL_FUSION_PROTOCOL.frozen.json",
    "scripts/run_track_a_006c_sequential_fusion.py",
    "scripts/verify_track_a_006c_freeze.py",
    "tests/test_track_a_006c_sequential_fusion.py",
}
EXPECTED_PARENT_SHA256 = "4e6d49ff091fc38c337d45800e5ede9e4576d39b3c1c0e7ac98a1a1fefbe1860"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "SEQUENTIAL_FUSION_FREEZE_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006c freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006c freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("006c freeze path set changed")

    protocol = json.loads(
        (AUDIT_ROOT / "SEQUENTIAL_FUSION_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    if protocol["status_at_freeze"] != "frozen_before_heldout_case_generation_or_target_execution":
        raise ValueError("006c prospective ordering changed")
    if protocol["benchmark"] != {
        "action_count": 3,
        "base_candidate_count": 4,
        "case_count": 64,
        "master_seed": "oia-track-a-006c-heldout-v1",
        "max_beliefs": 100000,
        "maximum_closed_depth": 6,
        "maximum_generation_attempts_per_stage": 2000,
        "maximum_reject_aware_depth": 8,
        "minimum_closed_depth": 2,
        "output_count": 3,
        "sentinel_count": 2,
        "state_count": 3,
    }:
        raise ValueError("006c benchmark configuration changed")
    if protocol["execution"]["expected_record_count"] != 960:
        raise ValueError("006c record accounting changed")
    if protocol["prefreeze_fixture"] != {
        "case_count": 3,
        "evidence_sha256": "5dc19aa8b568fcd29126acacd4867277aea7f18f8782ea96219e8dbad566b2b2",
        "record_count": 45,
        "records_jsonl_sha256": "5789e01ec39c7046f59f2a822e5bb382a472ed2e4c63a97e7097bfbf7516574b",
        "result_sha256": "6432dafa92304fe597e7a3d4cb0bbdedbe7cfee1862a96899b60a74bd76b10d6",
        "seed": "oia-track-a-006c-fixture-v1",
        "used_benchmark_seed": False,
    }:
        raise ValueError("006c fixture provenance changed")
    development = json.loads(
        (AUDIT_ROOT / "OPENED_SEQUENTIAL_DEVELOPMENT.json").read_text(
            encoding="utf-8"
        )
    )
    if development["retrospective_fusion"]["outside_detected"] != 42:
        raise ValueError("006c opened-development result changed")
    parent_path = ROOT / protocol["baseline"]["parent_runner"]
    if sha256(parent_path) != EXPECTED_PARENT_SHA256:
        raise ValueError("006c parent runner changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006c",
                "benchmark_cases_generated": 0,
                "benchmark_targets_executed": 0,
                "manifest_entries": len(observed),
                "pass": True,
                "status": "sequential_fusion_frozen_pre_outcome",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
