#!/usr/bin/env python3
"""Verify the frozen Track A 005a candidate-behavior/OIA execution substrate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
EXPECTED_PACKAGE_SHA256 = "9ae478a842b942bc80f3ff62063e4780d8097018384971d83db12fd6d87b167a"
EXPECTED_MANIFEST_PATHS = {
    "audits/track-a-005a/BEHAVIOR_AND_OIA_PROTOCOL.frozen.json",
    "audits/track-a-005a/PREEXECUTION_RUNTIME.json",
    "audits/track-a-005a/PREEXECUTION_RUNTIME_BUILD_ERRATUM.pre-candidate.json",
    "runtime/track-a-005a/Dockerfile",
    "runtime/track-a-005a/candidate_runner.py",
    "runtime/track-a-005a/requirements-aarch64.txt",
    "scripts/prepare_track_a_005a_admission.py",
    "scripts/run_track_a_005a_admission_and_oia.py",
    "scripts/verify_track_a_005a_behavior_outcome.py",
    "scripts/verify_track_a_005a_preexecution.py",
    "tests/fixtures/track-a-005a/synthetic_candidate/candidate.py",
    "tests/test_track_a_005a_admission.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> object:
    return json.loads((AUDIT_ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    observed_paths: set[str] = set()
    for line in (AUDIT_ROOT / "PREEXECUTION_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"preexecution checksum mismatch: {relative}")
        if relative in observed_paths:
            raise ValueError(f"duplicate preexecution path: {relative}")
        observed_paths.add(relative)
    if observed_paths != EXPECTED_MANIFEST_PATHS:
        raise ValueError("preexecution manifest path set changed")

    protocol = load("BEHAVIOR_AND_OIA_PROTOCOL.frozen.json")
    if protocol["status_at_freeze"] != "frozen_before_generated_candidate_source_open_or_execution":
        raise ValueError("preexecution ordering changed")
    if protocol["candidate_source"]["candidate_package_sha256"] != EXPECTED_PACKAGE_SHA256:
        raise ValueError("candidate package protocol pin changed")
    if protocol["candidate_source"]["candidate_source_open_before_this_freeze"] is not False:
        raise ValueError("candidate source access ordering changed")
    if protocol["action_language"]["word_count"] != 14:
        raise ValueError("action language changed")
    if protocol["adapter_and_oia"]["observation_fields"] != [
        "final_frame_sha256",
        "status",
    ]:
        raise ValueError("adapter observable boundary changed")
    if protocol["epistemic_ordering"]["held_out_post_p0_payloads_read"] != 0:
        raise ValueError("held-out outcome was accessed before separator selection")

    generation = json.loads(
        (AUDIT_ROOT / "candidate-generation" / "GENERATION_RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    accepted = [
        row["candidate_id"]
        for row in generation["candidate_records"]
        if row["status"] == "structurally_accepted_not_executed"
    ]
    if accepted != ["C0006", "C0008"]:
        raise ValueError("accepted generation frontier changed")
    if sha256(AUDIT_ROOT / "candidate-generation" / "CANDIDATE_PACKAGE.zip") != EXPECTED_PACKAGE_SHA256:
        raise ValueError("candidate package bytes changed")

    runtime = load("PREEXECUTION_RUNTIME.json")
    if runtime["status"] != "frozen_before_generated_candidate_source_open_or_execution":
        raise ValueError("runtime ordering changed")
    if runtime["runtime"]["base_image_id"] != "sha256:644d899fa00c3a9fc16cc05f94ee5d078653891fe55659cd8e51fb1126027051":
        raise ValueError("base isolation image changed")
    if runtime["runtime"]["python"] != "3.12.11" or runtime["runtime"]["numpy"] != "2.2.6":
        raise ValueError("runtime dependency versions changed")
    for record in runtime["source_pins"]:
        path = ROOT / record["path"]
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"preexecution source pin changed: {record['path']}")
    smoke = runtime["synthetic_smoke_test"]
    if (
        smoke["status"] != "pass"
        or smoke["p0_replay_exact"] is not True
        or smoke["word"] != ["ACTION6", "ACTION7"]
        or smoke["candidate_generated_by_005a"] is not False
    ):
        raise ValueError("synthetic smoke evidence changed")
    boundary = runtime["execution_boundary"]
    for field in (
        "generated_candidate_source_opened",
        "generated_candidate_processes",
        "oia_processes",
        "real_arc_actions",
        "held_out_post_p0_payloads_read",
    ):
        if boundary[field] != 0:
            raise ValueError(f"preexecution boundary crossed: {field}")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "image_id": runtime["runtime"]["image_id"],
                "manifest_entries": len(observed_paths),
                "pass": True,
                "status": "behavior_and_oia_preexecution_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
