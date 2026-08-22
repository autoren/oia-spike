#!/usr/bin/env python3
"""Verify the prospective Track A 005d step-2 archival-outcome freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005d"
EXPECTED_BEHAVIOR_SHA256 = "e177ee9bbf86d0d88faee64915858beb22ff87518e7d83b32cb0f110b6e9a840"
EXPECTED_PATHS = {
    "audits/track-a-005d/README.md",
    "audits/track-a-005d/STEP2_ARCHIVE_OUTCOME_PROTOCOL.frozen.json",
    "scripts/extract_track_a_005d_step2_outcome.py",
    "scripts/verify_track_a_005d_freeze.py",
    "scripts/verify_track_a_005d_outcome.py",
    "tests/test_track_a_005d_step2_outcome.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed = set()
    for line in (AUDIT_ROOT / "STEP2_OUTCOME_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005d freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 005d freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("005d freeze path set changed")
    protocol = json.loads(
        (AUDIT_ROOT / "STEP2_ARCHIVE_OUTCOME_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    if protocol["status_at_freeze"] != "frozen_after_action7_merge_before_step2_payload_access":
        raise ValueError("005d prospective ordering changed")
    if protocol["prospective_parent"]["selected_next_action"] != "ACTION7":
        raise ValueError("005d target action changed")
    if protocol["header_only_inventory_before_freeze"]["step2_payloads_read"] != 0:
        raise ValueError("005d step-2 payload read before freeze")
    if protocol["header_only_inventory_before_freeze"]["expected_nonmetadata_plus_metadata_file_counts"] != [11, 11, 3, 11, 11]:
        raise ValueError("005d header inventory changed")
    if protocol["archive"]["sha256"] != "c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93":
        raise ValueError("005d archive pin changed")
    behavior = ROOT / "audits" / "track-a-005c" / "behavior-outcome" / "ADMISSION_AND_OIA_RESULT.json"
    if sha256(behavior) != EXPECTED_BEHAVIOR_SHA256:
        raise ValueError("005d merged behavior result changed")
    result = json.loads(behavior.read_text(encoding="utf-8"))
    if (
        result["gate_verdict"] != "maintenance_revised_separator_selected_pre_step2"
        or result["selected_next_action"] != "ACTION7"
        or result["execution_accounting"]["step_2_or_later_payloads_read"] != 0
    ):
        raise ValueError("005d prospective behavior boundary changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005d",
                "manifest_entries": len(observed),
                "pass": True,
                "status": "step2_archival_outcome_frozen",
                "target_action": "ACTION7",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
