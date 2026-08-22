#!/usr/bin/env python3
"""Verify the prospective Track A 005c missing-import maintenance freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005c"
PARENT_PACKAGE = ROOT / "audits" / "track-a-005b" / "revision-generation" / "CANDIDATE_PACKAGE.zip"
PARENT_OUTCOME = ROOT / "audits" / "track-a-005b" / "behavior-outcome" / "ADMISSION_AND_OIA_RESULT.json"
EXPECTED_PACKAGE_SHA256 = "a49a8012b0f7f130feb5c32bfb32825ad4426d7c2203fba6e532165c1fd884d4"
EXPECTED_OUTCOME_SHA256 = "d85d1496a11330c0064f4e87a5b1ba336437ff551c04204027ac3f9f14f9c3e7"
EXPECTED_IMAGE_ID = "sha256:32272ac8ae641808d6b6328bcdb7210746292ea12e4aeea8b69ef93cab49ee2b"
EXPECTED_PATHS = {
    "audits/track-a-005c/MISSING_IMPORT_NORMALIZATION_PROTOCOL.frozen.json",
    "audits/track-a-005c/README.md",
    "scripts/normalize_track_a_005c_candidates.py",
    "scripts/prepare_track_a_005c_admission.py",
    "scripts/run_track_a_005c_admission_and_oia.py",
    "scripts/verify_track_a_005c_behavior_outcome.py",
    "scripts/verify_track_a_005c_freeze.py",
    "scripts/verify_track_a_005c_normalization_result.py",
    "tests/test_track_a_005c_normalization.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed = set()
    for line in (AUDIT_ROOT / "MISSING_IMPORT_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005c freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 005c freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("005c freeze path set changed")
    if sha256(PARENT_PACKAGE) != EXPECTED_PACKAGE_SHA256:
        raise ValueError("005c parent package changed")
    if sha256(PARENT_OUTCOME) != EXPECTED_OUTCOME_SHA256:
        raise ValueError("005c parent blocker changed")
    parent_result = json.loads(PARENT_OUTCOME.read_text(encoding="utf-8"))
    if (
        parent_result["gate_verdict"] != "revision_generation_or_calibration_blocker"
        or parent_result["execution_accounting"]["candidate_processes"] != 8
        or parent_result["execution_accounting"]["oia_processes"] != 0
        or parent_result["execution_accounting"]["step_2_or_later_payloads_read"] != 0
    ):
        raise ValueError("005c parent blocker boundary changed")
    protocol = json.loads(
        (AUDIT_ROOT / "MISSING_IMPORT_NORMALIZATION_PROTOCOL.frozen.json").read_text(
            encoding="utf-8"
        )
    )
    if protocol["status_at_freeze"] != "frozen_before_any_source_normalization_or_candidate_reexecution":
        raise ValueError("005c ordering changed")
    allowed = protocol["allowed_normalization"]
    if (
        allowed["transformation"]
        != "Prepend the exact ASCII bytes `import copy\\n` to the unchanged parent source."
        or allowed["maximum_edits_per_candidate"] != 1
        or allowed["other_name_import_or_semantic_repairs"] is not False
        or allowed["model_or_repair_inferences"] != 0
    ):
        raise ValueError("005c normalization scope changed")
    gate = protocol["post_normalization_gate"]
    if (
        gate["runtime_image_id"] != EXPECTED_IMAGE_ID
        or gate["calibration_exactness_unchanged"] is not True
        or gate["step_2_or_later_payloads_read"] != 0
    ):
        raise ValueError("005c post-normalization gate changed")
    expected_sources = {
        row["candidate_id"]: row["sha256"] for row in protocol["parent"]["candidate_sources"]
    }
    with zipfile.ZipFile(PARENT_PACKAGE) as archive:
        manifest = json.loads(archive.read("CANDIDATE_MANIFEST.json"))
        observed_sources = {
            row["candidate_id"]: hashlib.sha256(
                archive.read(f"candidates/{row['candidate_id']}/candidate.py")
            ).hexdigest()
            for row in manifest["candidates"]
        }
    if observed_sources != expected_sources:
        raise ValueError("005c parent source pin set changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005c",
                "candidate_count": len(expected_sources),
                "manifest_entries": len(observed),
                "pass": True,
                "status": "missing_import_maintenance_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
