#!/usr/bin/env python3
"""Verify the frozen Track A 005a public archival-outcome extraction gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
EXPECTED_PATHS = {
    "audits/track-a-005a/ARCHIVE_OUTCOME_PROTOCOL.frozen.json",
    "scripts/extract_track_a_005a_archive_outcome.py",
    "scripts/verify_track_a_005a_archive_outcome.py",
    "scripts/verify_track_a_005a_archive_outcome_freeze.py",
    "tests/test_track_a_005a_archive_outcome.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed: set[str] = set()
    for line in (AUDIT_ROOT / "ARCHIVE_OUTCOME_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"archive-outcome freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate archive-outcome freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("archive-outcome freeze path set changed")

    protocol = json.loads(
        (AUDIT_ROOT / "ARCHIVE_OUTCOME_PROTOCOL.frozen.json").read_text(encoding="utf-8")
    )
    if protocol["status_at_freeze"] != "frozen_after_separator_merge_before_post_p0_payload_access":
        raise ValueError("archival outcome ordering changed")
    if protocol["target_action"] != "ACTION6":
        raise ValueError("archival target action changed")
    if protocol["epistemic_ordering"]["post_p0_payloads_read_before_this_freeze"] != 0:
        raise ValueError("post-P0 payload access occurred before archive outcome freeze")
    if protocol["archive"]["sha256"] != "c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93":
        raise ValueError("source archive pin changed")
    if len(protocol["run_roots_in_order"]) != 5 or len(protocol["exact_step1_files_per_run"]) != 11:
        raise ValueError("archival outcome member boundary changed")
    behavior_result = AUDIT_ROOT / "behavior-outcome" / "ADMISSION_AND_OIA_RESULT.json"
    if sha256(behavior_result) != protocol["epistemic_ordering"]["behavior_result_sha256"]:
        raise ValueError("merged separator evidence pin changed")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "manifest_entries": len(observed),
                "pass": True,
                "status": "archive_outcome_extraction_frozen",
                "target_action": protocol["target_action"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
