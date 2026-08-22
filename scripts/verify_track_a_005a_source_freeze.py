#!/usr/bin/env python3
"""Verify the Track A 005a held-out source-selection freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> object:
    return json.loads((AUDIT_ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    entries = 0
    for line in (AUDIT_ROOT / "SOURCE_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"source-freeze checksum mismatch: {relative}")
        entries += 1

    pin = load("SOURCE_ARCHIVE_PIN.json")
    if pin["file"]["size_bytes"] != 797_835_543:
        raise ValueError("archive size pin changed")
    if pin["file"]["sha256"] != "c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93":
        raise ValueError("archive SHA-256 pin changed")
    if pin["license"] != "CC-BY-4.0" or pin["access"] != "open":
        raise ValueError("source license/access changed")

    protocol = load("SOURCE_UNIVERSE_PROTOCOL.frozen.json")
    if protocol["status_at_freeze"] != "frozen_before_selection_algorithm_execution":
        raise ValueError("source-selection ordering changed")
    if protocol["prior_access"]["member_payloads_read"] != 0:
        raise ValueError("source content was accessed before freeze")
    if protocol["candidate_route"]["archived_candidate_programs_allowed"] is not False:
        raise ValueError("post-P0 leakage boundary changed")
    if protocol["selection_rule"]["excluded_games"] != ["ls20"]:
        raise ValueError("opened-game exclusion changed")

    sys.path.insert(0, str(ROOT / "scripts"))
    import inventory_track_a_005a_source as inventory

    if tuple(protocol["source_universe"]["expected_runs"]) != inventory.EXPECTED_RUNS:
        raise ValueError("run-root constants disagree")
    if protocol["selection_rule"]["audit_id"] != inventory.AUDIT_ID:
        raise ValueError("selection salt changed")
    if protocol["selection_rule"]["archive_sha256"] != inventory.EXPECTED_ARCHIVE_SHA256:
        raise ValueError("selection archive pin changed")

    print(
        json.dumps(
            {
                "audit_id": inventory.AUDIT_ID,
                "manifest_entries": entries,
                "pass": True,
                "status": "source_selection_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
