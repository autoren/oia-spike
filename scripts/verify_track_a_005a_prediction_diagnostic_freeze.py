#!/usr/bin/env python3
"""Verify the frozen Track A 005a post-outcome prediction diagnostic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
EXPECTED_PATHS = {
    "audits/track-a-005a/PREDICTION_ERROR_DIAGNOSTIC_PROTOCOL.frozen.json",
    "runtime/track-a-005a/prediction_diagnostic_runner.py",
    "scripts/run_track_a_005a_prediction_diagnostic.py",
    "scripts/verify_track_a_005a_prediction_diagnostic.py",
    "scripts/verify_track_a_005a_prediction_diagnostic_freeze.py",
    "tests/test_track_a_005a_prediction_diagnostic.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed = set()
    for line in (AUDIT_ROOT / "PREDICTION_DIAGNOSTIC_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"prediction diagnostic freeze mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate prediction diagnostic path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("prediction diagnostic manifest path set changed")
    protocol = json.loads(
        (AUDIT_ROOT / "PREDICTION_ERROR_DIAGNOSTIC_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    if protocol["status_at_freeze"] != "frozen_after_actual_outcome_before_candidate_raster_recovery":
        raise ValueError("prediction diagnostic ordering changed")
    if protocol["interpretation"]["acceptance_threshold"] is not None:
        raise ValueError("post-hoc diagnostic threshold introduced")
    if protocol["outcome_boundary"]["later_step_payloads_authorized"] is not False:
        raise ValueError("later archival steps were authorized")
    if protocol["candidate_boundary"]["raster_access_before_this_freeze"] is not False:
        raise ValueError("candidate raster ordering changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "manifest_entries": len(observed),
                "pass": True,
                "status": "prediction_error_diagnostic_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
