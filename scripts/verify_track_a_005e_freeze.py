#!/usr/bin/env python3
"""Verify the post-acquisition, pre-action Track A 005e freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005e"
EXPECTED_005C_SHA256 = "e177ee9bbf86d0d88faee64915858beb22ff87518e7d83b32cb0f110b6e9a840"
EXPECTED_005D_SHA256 = "d09a71682086dd0871d1035948f7f0091f86139148086d2676321a850bb219c5"
EXPECTED_PATHS = {
    "README.md",
    "audits/track-a-005e/LOCAL_OUTCOME_PROTOCOL.frozen.json",
    "audits/track-a-005e/OFFICIAL_SOURCE_ACQUISITION.json",
    "audits/track-a-005e/README.md",
    "audits/track-a-005e/RUNTIME_REQUIREMENTS.lock.txt",
    "scripts/run_track_a_005e_local_outcome.py",
    "scripts/verify_track_a_005e_freeze.py",
    "tests/test_track_a_005e_local_outcome.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observed: set[str] = set()
    checksum_path = AUDIT_ROOT / "LOCAL_OUTCOME_FREEZE_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005e freeze checksum mismatch: {relative}")
        if relative in observed:
            raise ValueError(f"duplicate 005e freeze path: {relative}")
        observed.add(relative)
    if observed != EXPECTED_PATHS:
        raise ValueError("005e freeze path set changed")

    acquisition = json.loads((AUDIT_ROOT / "OFFICIAL_SOURCE_ACQUISITION.json").read_text(encoding="utf-8"))
    accounting = acquisition["access_accounting"]
    for field in (
        "anonymous_api_keys_retained",
        "candidate_processes",
        "game_class_imports",
        "game_source_executions",
        "model_calls",
        "non_acquisition_service_calls",
        "oia_processes",
        "private_or_sealed_payloads",
        "real_arc_actions",
        "resets",
    ):
        if accounting[field] != 0:
            raise ValueError(f"005e acquisition boundary crossed: {field}")
    if acquisition["source"]["committed_to_repository"]:
        raise ValueError("005e source payload must remain uncommitted")

    protocol = json.loads((AUDIT_ROOT / "LOCAL_OUTCOME_PROTOCOL.frozen.json").read_text(encoding="utf-8"))
    if protocol["status_at_freeze"] != "frozen_after_source_acquisition_before_source_execution_reset_or_action":
        raise ValueError("005e prospective ordering changed")
    if protocol["frozen_parent"]["selected_next_action"] != "ACTION7":
        raise ValueError("005e target action changed")
    if protocol["action_schedule"]["ordered_coordinates"] != [
        {
            "opened_step1_metadata_multiplicity": 3,
            "opened_step1_metadata_sha256": "523fee5f9c4205aefff92eb0ad395f9bd3c7d5e207b3fd08cd21201740ae8ee1",
            "x": 4,
            "y": 59,
        },
        {
            "opened_step1_metadata_multiplicity": 2,
            "opened_step1_metadata_sha256": "2bce325b3a22f13605d8faeebeb9f44ae9832a871a3a27d16d24ddd12babaa15",
            "x": 48,
            "y": 15,
        },
    ]:
        raise ValueError("005e coordinate schedule changed")
    if protocol["action_schedule"]["repetitions_per_coordinate"] != 2:
        raise ValueError("005e repetition schedule changed")
    if protocol["execution_boundary"]["maximum_action7_interventions"] != 4:
        raise ValueError("005e action cap changed")
    if protocol["environment"]["source_sha256"] != acquisition["source"]["sha256"]:
        raise ValueError("005e source provenance changed")

    parent_005c = ROOT / "audits/track-a-005c/behavior-outcome/ADMISSION_AND_OIA_RESULT.json"
    parent_005d = ROOT / "audits/track-a-005d/step2-outcome/STEP2_ARCHIVE_OUTCOME_RESULT.json"
    if sha256(parent_005c) != EXPECTED_005C_SHA256 or sha256(parent_005d) != EXPECTED_005D_SHA256:
        raise ValueError("005e parent result changed")
    result_005c = json.loads(parent_005c.read_text(encoding="utf-8"))
    result_005d = json.loads(parent_005d.read_text(encoding="utf-8"))
    if result_005c["selected_next_action"] != "ACTION7":
        raise ValueError("005e parent OIA action changed")
    if result_005d["gate_verdict"] != "no_matching_recorded_step2_action":
        raise ValueError("005e archive-blocker premise changed")
    print(json.dumps({
        "audit_id": "OIA-1-TRACK-A-005e",
        "manifest_entries": len(observed),
        "pass": True,
        "source_executions": 0,
        "status": "local_outcome_frozen_pre_action",
        "target_action": "ACTION7",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
