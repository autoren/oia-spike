#!/usr/bin/env python3
"""Verify the Track A 005d public archival step-2 outcome when present."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005d"
OUTCOME_ROOT = AUDIT_ROOT / "step2-outcome"
ALLOWED = {
    "no_matching_recorded_step2_action",
    "recorded_step2_outcome_inconsistent_across_runs",
    "revised_step2_matches_one_candidate",
    "revised_step2_matches_persistence_only",
    "revised_step2_matches_candidate_and_persistence",
    "revised_step2_outside_candidate_frontier_and_persistence",
}

sys.path.insert(0, str(ROOT / "scripts"))
import extract_track_a_005d_step2_outcome as extraction


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    if not OUTCOME_ROOT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005d", "status": "preoutcome"}))
        return
    checksum_path = AUDIT_ROOT / "STEP2_OUTCOME_SHA256SUMS.txt"
    if not checksum_path.is_file():
        raise ValueError("005d outcome checksum manifest missing")
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005d outcome checksum mismatch: {relative}")
    result_path = OUTCOME_ROOT / "STEP2_ARCHIVE_OUTCOME_RESULT.json"
    evidence_path = OUTCOME_ROOT / "STEP2_ARCHIVE_OUTCOME_EVIDENCE.zip"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["gate_verdict"] not in ALLOWED or result["target_action"] != "ACTION7":
        raise ValueError("unexpected 005d outcome verdict")
    if result["candidate_predictions"] != extraction.candidate_predictions():
        raise ValueError("005d candidate predictions changed")
    if result["persistence_baseline"] != extraction.P1_PERSISTENCE:
        raise ValueError("005d persistence baseline changed")
    accounting = result["access_accounting"]
    if accounting["step2_metadata_payloads_read"] != 5:
        raise ValueError("005d metadata accounting changed")
    for field in (
        "nonmatching_run_frame_payloads_read",
        "step3_or_later_payloads_read",
        "candidate_processes",
        "oia_processes",
        "model_or_api_calls",
        "real_arc_actions",
    ):
        if accounting[field] != 0:
            raise ValueError(f"005d access boundary crossed: {field}")
    if evidence_path.stat().st_size != result["evidence_package"]["size_bytes"] or sha256(evidence_path) != result["evidence_package"]["sha256"]:
        raise ValueError("005d evidence package changed")
    metadata_actions = {row["run_root"]: row["action_id"] for row in result["metadata_records"]}
    matching = [run for run in extraction.RUN_ROOTS if metadata_actions[run] == "ACTION7"]
    if result["matching_run_roots"] != matching:
        raise ValueError("005d matching-run selection changed")
    expected_names = {
        f"runs/{run}/step_0002_metadata.json" for run in extraction.RUN_ROOTS
    } | {
        f"runs/{run}/{basename}"
        for run in matching
        for basename in extraction.EXPECTED_BASENAMES[run]
    }
    with zipfile.ZipFile(evidence_path) as archive:
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("005d evidence package duplicate paths")
        if {info.filename for info in infos} != expected_names:
            raise ValueError("005d evidence package path set changed")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise ValueError(f"unsafe 005d evidence path: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0) or (info.external_attr >> 16) != 0o100444:
                raise ValueError(f"005d deterministic ZIP metadata changed: {info.filename}")
        observed_outcomes = []
        for row in result["outcomes"]:
            run = row["run_root"]
            final = archive.read(f"runs/{run}/step_0002_final.txt")
            metadata = json.loads(archive.read(f"runs/{run}/step_0002_metadata.json"))
            observation = {
                "final_frame_sha256": extraction.validate_frame(final),
                "status": extraction.STATE_TO_STATUS[metadata["state"]],
            }
            if row["observation"] != observation:
                raise ValueError(f"005d observation changed: {run}")
            if row["matching_candidates"] != [
                candidate
                for candidate, prediction in result["candidate_predictions"].items()
                if prediction == observation
            ]:
                raise ValueError(f"005d candidate comparison changed: {run}")
            if row["matches_persistence_baseline"] != (observation == extraction.P1_PERSISTENCE):
                raise ValueError(f"005d persistence comparison changed: {run}")
            observed_outcomes.append(row)
    if accounting["matching_action_nonmetadata_payloads_read"] != sum(
        len(extraction.EXPECTED_BASENAMES[run]) - 1 for run in matching
    ):
        raise ValueError("005d matching-frame accounting changed")
    if result["gate_verdict"] != extraction.verdict_for(observed_outcomes):
        raise ValueError("005d verdict changed")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005d",
                "gate_verdict": result["gate_verdict"],
                "matching_runs": len(matching),
                "pass": True,
                "target_action": "ACTION7",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
