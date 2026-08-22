#!/usr/bin/env python3
"""Verify the pre-benchmark Track A 006a controlled open-world freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-006a"
EXPECTED_PATHS = {
    "README.md",
    "audits/track-a-006a/CONTROLLED_OPEN_WORLD_PROTOCOL.frozen.json",
    "audits/track-a-006a/README.md",
    "scripts/run_track_a_006a_controlled_open_world.py",
    "scripts/verify_track_a_006a_freeze.py",
    "tests/test_track_a_006a_controlled_open_world.py",
}
EXPECTED_BASELINE = {
    "baseline/oia-v0.2.1/src/ontology_auditor/__init__.py": "321863cc19ba7b6bb22593aa3f20f991cbbd12930afbff4dc9dccf4cc7b15a3b",
    "baseline/oia-v0.2.1/src/ontology_auditor/model.py": "9d622641f267e7dc1e99302060ac0a3a7ecd654e46f3162c9605c9ba602eca24",
    "baseline/oia-v0.2.1/src/ontology_auditor/synthesis.py": "7df543e8af759a26ea2d5c256de4a66fb60a33dc3a42b2fea0d720c430f21f07",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed: set[str] = set()
    for line in (AUDIT_ROOT / "CONTROLLED_OPEN_WORLD_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"006a freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 006a freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("006a freeze path set changed")

    protocol = json.loads(
        (AUDIT_ROOT / "CONTROLLED_OPEN_WORLD_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    if protocol["status_at_freeze"] != "frozen_before_benchmark_case_generation_or_target_execution":
        raise ValueError("006a prospective ordering changed")
    benchmark = protocol["benchmark"]
    if benchmark != {
        "action_count": 3,
        "candidate_count": 4,
        "case_count": 64,
        "master_seed": "oia-track-a-006a-benchmark-v1",
        "max_beliefs": 100000,
        "maximum_generation_attempts_per_case": 2000,
        "maximum_oia_depth": 6,
        "minimum_oia_depth": 2,
        "output_count": 3,
        "random_trials_per_target": 32,
        "state_count": 3,
    }:
        raise ValueError("006a benchmark configuration changed")
    if protocol["execution"]["expected_record_count"] != 10880:
        raise ValueError("006a record accounting changed")
    if protocol["prefreeze_fixture"]["used_benchmark_seed"]:
        raise ValueError("006a benchmark seed was exposed through fixture")
    if protocol["prefreeze_fixture"]["record_count"] != 90:
        raise ValueError("006a fixture accounting changed")
    if protocol["baseline"]["source_sha256"] != EXPECTED_BASELINE:
        raise ValueError("006a baseline manifest changed")
    for relative, expected in EXPECTED_BASELINE.items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"006a baseline source changed: {relative}")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-006a",
                "benchmark_cases_generated": 0,
                "benchmark_targets_executed": 0,
                "manifest_entries": len(observed),
                "pass": True,
                "status": "controlled_open_world_frozen_pre_benchmark",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

