#!/usr/bin/env python3
"""Verify a committed Track A 005b revision package without executing it."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005b"
RESULT_ROOT = AUDIT_ROOT / "revision-generation"
RESULT_PATH = RESULT_ROOT / "GENERATION_RESULT.json"
PACKAGE_PATH = RESULT_ROOT / "CANDIDATE_PACKAGE.zip"
STANCES_PATH = AUDIT_ROOT / "REVISION_HYPOTHESIS_STANCES.frozen.json"
INPUT_MANIFEST_PATH = AUDIT_ROOT / "revision-input" / "REVISION_INPUT_MANIFEST.json"
sys.path.insert(0, str(ROOT / "scripts"))
from generate_track_a_005a_candidates import validate_code


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    if not RESULT_PATH.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005b", "status": "pregeneration"}))
        return
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result["status"] not in {"revision_generation_feasible", "revision_generation_blocked"}:
        raise ValueError("unexpected revision generation verdict")
    if result["revision_input_manifest_sha256"] != sha256(INPUT_MANIFEST_PATH):
        raise ValueError("revision input identity changed")
    package = result["package"]
    if PACKAGE_PATH.stat().st_size != package["size_bytes"] or sha256(PACKAGE_PATH) != package["sha256"]:
        raise ValueError("revision package identity changed")
    frozen_stances = json.loads(STANCES_PATH.read_text(encoding="utf-8"))["stances"]
    expected_identity = [(row["candidate_id"], row["stance_id"]) for row in frozen_stances]
    observed_identity = [
        (row["candidate_id"], row["stance_id"]) for row in result["candidate_records"]
    ]
    if observed_identity != expected_identity:
        raise ValueError("revision candidate identity or order changed")

    with zipfile.ZipFile(PACKAGE_PATH) as archive:
        infos = archive.infolist()
        if len(infos) != len({item.filename for item in infos}):
            raise ValueError("revision package has duplicate entries")
        if [item.filename for item in infos] != sorted(item.filename for item in infos):
            raise ValueError("revision package order changed")
        for item in infos:
            pure = PurePosixPath(item.filename)
            if pure.is_absolute() or ".." in pure.parts or item.is_dir():
                raise ValueError(f"unsafe revision package path: {item.filename}")
            if item.date_time != (1980, 1, 1, 0, 0, 0):
                raise ValueError(f"revision package timestamp changed: {item.filename}")
            if (item.external_attr >> 16) != 0o100444:
                raise ValueError(f"revision package mode changed: {item.filename}")
        manifest_bytes = archive.read("CANDIDATE_MANIFEST.json")
        if sha256_bytes(manifest_bytes) != package["manifest_sha256"]:
            raise ValueError("revision manifest hash changed")
        manifest = json.loads(manifest_bytes)
        if manifest["audit_id"] != "OIA-1-TRACK-A-005b":
            raise ValueError("revision package audit changed")
        expected_names = {"CANDIDATE_MANIFEST.json"}
        manifest_identity = []
        for candidate in manifest["candidates"]:
            name = f"candidates/{candidate['candidate_id']}/candidate.py"
            code = archive.read(name)
            if len(code) != candidate["candidate_size_bytes"]:
                raise ValueError(f"revision candidate size mismatch: {candidate['candidate_id']}")
            if sha256_bytes(code) != candidate["candidate_sha256"]:
                raise ValueError(f"revision candidate hash mismatch: {candidate['candidate_id']}")
            if candidate["source_representation"] not in {
                "literal_markers",
                "single_python_or_plain_fence",
                "raw_python",
            }:
                raise ValueError("unexpected source representation")
            if validate_code(code.decode("utf-8"))["result"] != "pass":
                raise ValueError(f"revision candidate structure changed: {candidate['candidate_id']}")
            expected_names.add(name)
            manifest_identity.append((candidate["candidate_id"], candidate["stance_id"]))
        if {item.filename for item in infos} != expected_names:
            raise ValueError("revision package entry set changed")

    accepted = [
        row
        for row in result["candidate_records"]
        if row["status"] == "structurally_accepted_not_executed"
    ]
    rejected = [
        row for row in result["candidate_records"] if row["status"] == "rejected_structural"
    ]
    accounting = result["accounting"]
    if accounting["requested_candidates"] != 8 or accounting["local_model_inferences"] != 8:
        raise ValueError("revision inference accounting changed")
    if accounting["structurally_accepted_candidates"] != len(accepted):
        raise ValueError("revision accepted accounting changed")
    if accounting["structurally_rejected_candidates"] != len(rejected):
        raise ValueError("revision rejected accounting changed")
    if manifest["candidate_count"] != len(accepted):
        raise ValueError("revision manifest count changed")
    if manifest_identity != [(row["candidate_id"], row["stance_id"]) for row in accepted]:
        raise ValueError("revision manifest and records disagree")
    if result["status"] == "revision_generation_feasible" and len(accepted) < 2:
        raise ValueError("feasible revision verdict has fewer than two candidates")
    if result["status"] == "revision_generation_blocked" and len(accepted) >= 2:
        raise ValueError("blocked revision verdict has a sufficient static frontier")
    for field in (
        "repair_inferences",
        "candidate_processes",
        "candidate_behavior_steps",
        "hosted_or_api_model_calls",
        "network_or_service_calls",
        "oia_processes",
        "step_2_or_later_payloads_read",
        "real_arc_actions",
    ):
        if accounting[field] != 0:
            raise ValueError(f"revision generation boundary crossed: {field}")
    if accounting["output_tokens_recorded"] != sum(
        row["output_token_count"] for row in result["candidate_records"]
    ):
        raise ValueError("revision output token accounting changed")
    print(
        json.dumps(
            {
                "accepted": len(accepted),
                "audit_id": result["audit_id"],
                "package_sha256": package["sha256"],
                "pass": True,
                "rejected": len(rejected),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
