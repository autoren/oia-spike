#!/usr/bin/env python3
"""Verify the Track A 005a P0 freeze and extraction when present."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
EVIDENCE_PATH = AUDIT_ROOT / "P0_EXTRACTION.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    entries = 0
    for line in (AUDIT_ROOT / "P0_FREEZE_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"P0-freeze checksum mismatch: {relative}")
        entries += 1
    protocol = json.loads(
        (AUDIT_ROOT / "P0_EXTRACTION_PROTOCOL.frozen.json").read_text(encoding="utf-8")
    )
    if protocol["status_at_freeze"] != "frozen_before_selected_p0_payload_access":
        raise ValueError("P0 extraction ordering changed")
    if protocol["selected_game"] != "su15":
        raise ValueError("held-out selected game changed")
    if not EVIDENCE_PATH.exists():
        print(
            json.dumps(
                {
                    "audit_id": "OIA-1-TRACK-A-005a",
                    "manifest_entries": entries,
                    "status": "p0_extraction_frozen",
                },
                sort_keys=True,
            )
        )
        return

    result = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if result["status"] != "selected_common_p0_extracted_and_validated":
        raise ValueError("P0 extraction status changed")
    if result["target_member_count"] != 15 or result["selected_game"] != "su15":
        raise ValueError("P0 extraction target changed")
    for filename, record in result["canonical_files"].items():
        path = ROOT / record["path"]
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"canonical P0 mismatch: {filename}")
        equality = result["validation"]["file_equality"][filename]
        if equality["all_five_byte_identical"] is not True:
            raise ValueError(f"P0 equality changed: {filename}")
        if set(equality["per_run_sha256"].values()) != {record["sha256"]}:
            raise ValueError(f"per-run P0 hashes disagree: {filename}")
    accounting = result["access_accounting"]
    if accounting["selected_p0_payloads_read"] != 15:
        raise ValueError("selected P0 read count changed")
    for field in (
        "nonselected_member_payloads_read",
        "candidate_files_read",
        "behavioral_traces_read",
        "scores_read",
        "candidate_processes",
        "model_or_api_calls",
        "oia_processes",
        "real_arc_actions",
    ):
        if accounting[field] != 0:
            raise ValueError(f"P0 extraction boundary crossed: {field}")
    print(
        json.dumps(
            {
                "audit_id": result["audit_id"],
                "evidence_sha256": sha256(EVIDENCE_PATH),
                "manifest_entries": entries,
                "pass": True,
                "selected_game": result["selected_game"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
