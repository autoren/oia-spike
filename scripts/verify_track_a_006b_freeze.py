#!/usr/bin/env python3
"""Verify the pre-outcome Track A 006b reject-aware freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-006b"
EXPECTED_PATHS = {
    "README.md",
    "audits/track-a-006b/OPENED_DEVELOPMENT_SELECTION.json",
    "audits/track-a-006b/README.md",
    "audits/track-a-006b/REJECT_AWARE_PROTOCOL.frozen.json",
    "scripts/run_track_a_006b_reject_aware.py",
    "scripts/verify_track_a_006b_freeze.py",
    "tests/test_track_a_006b_reject_aware.py",
}
EXPECTED_PARENT_SHA256 = "ffa2c2916662225e06041a4346e8a255953a1addb62b480d412637f8851d1231"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "REJECT_AWARE_FREEZE_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006b freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006b freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("006b freeze path set changed")

    protocol = json.loads(
        (AUDIT_ROOT / "REJECT_AWARE_PROTOCOL.frozen.json").read_text(encoding="utf-8")
    )
    if protocol["status_at_freeze"] != "frozen_before_heldout_case_generation_or_target_execution":
        raise ValueError("006b prospective ordering changed")
    if protocol["benchmark"] != {
        "action_count": 3,
        "base_candidate_count": 4,
        "case_count": 64,
        "master_seed": "oia-track-a-006b-heldout-v1",
        "max_beliefs": 100000,
        "maximum_closed_depth": 6,
        "maximum_generation_attempts_per_stage": 2000,
        "maximum_reject_aware_depth": 8,
        "minimum_closed_depth": 2,
        "output_count": 3,
        "sentinel_count": 2,
        "state_count": 3,
    }:
        raise ValueError("006b benchmark configuration changed")
    if protocol["execution"]["expected_record_count"] != 960:
        raise ValueError("006b record accounting changed")
    if protocol["prefreeze_fixture"] != {
        "case_count": 3,
        "evidence_sha256": "1bb2e90d5c38a0c6a2254ccbbf996340407f124a3f262b9a7dd3efc6e7729d81",
        "record_count": 45,
        "records_jsonl_sha256": "bd9525fc73a05346b1bd211eee593ce56578ec11fc819edf730206cf45b8015a",
        "result_sha256": "82d0379fd2721de78e5b909e833daa694345ce9c4838ad394f5c1cce87651cd0",
        "seed": "oia-track-a-006b-fixture-v1",
        "used_benchmark_seed": False,
    }:
        raise ValueError("006b fixture provenance changed")
    selection = json.loads(
        (AUDIT_ROOT / "OPENED_DEVELOPMENT_SELECTION.json").read_text(encoding="utf-8")
    )
    if selection["selection"]["sentinel_count"] != 2:
        raise ValueError("006b selected sentinel count changed")
    if [item["outside_detected"] for item in selection["observations"]] != [6, 9, 9, 9]:
        raise ValueError("006b opened-development counts changed")
    parent_path = ROOT / protocol["baseline"]["parent_runner"]
    if sha256(parent_path) != EXPECTED_PARENT_SHA256:
        raise ValueError("006b parent runner changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006b",
                "benchmark_cases_generated": 0,
                "benchmark_targets_executed": 0,
                "manifest_entries": len(observed),
                "pass": True,
                "selected_sentinel_count": 2,
                "status": "reject_aware_frozen_pre_outcome",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
