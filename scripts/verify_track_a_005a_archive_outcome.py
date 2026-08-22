#!/usr/bin/env python3
"""Independently verify the Track A 005a archival outcome when present."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
OUTCOME_ROOT = AUDIT_ROOT / "archive-outcome"
RESULT_PATH = OUTCOME_ROOT / "ARCHIVE_OUTCOME_RESULT.json"
EVIDENCE_PATH = OUTCOME_ROOT / "ARCHIVE_OUTCOME_EVIDENCE.zip"
ALLOWED_VERDICTS = {
    "separator_outcome_matches_one_candidate",
    "separator_outcome_outside_candidate_frontier",
    "recorded_outcome_inconsistent_across_runs",
    "no_matching_recorded_p0_action",
}

sys.path.insert(0, str(ROOT / "scripts"))
import extract_track_a_005a_archive_outcome as extraction


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    if not OUTCOME_ROOT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005a", "status": "archive_outcome_unopened"}))
        return
    checksum_manifest = AUDIT_ROOT / "ARCHIVE_OUTCOME_SHA256SUMS.txt"
    for line in checksum_manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"archive outcome checksum mismatch: {relative}")

    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result["gate_verdict"] not in ALLOWED_VERDICTS or result["target_action"] != "ACTION6":
        raise ValueError("unexpected archive outcome verdict")
    package = result["evidence_package"]
    if EVIDENCE_PATH.stat().st_size != package["size_bytes"] or sha256(EVIDENCE_PATH) != package["sha256"]:
        raise ValueError("archive outcome evidence package changed")

    expected_names = {
        f"runs/{run}/step_0001_metadata.json" for run in extraction.RUN_ROOTS
    }
    expected_names.update(
        f"runs/{run}/{basename}"
        for run in result["matching_run_roots"]
        for basename in extraction.STEP1_BASENAMES
    )
    with zipfile.ZipFile(EVIDENCE_PATH) as archive:
        infos = archive.infolist()
        if len(infos) != len({item.filename for item in infos}):
            raise ValueError("archive outcome package has duplicate entries")
        if [item.filename for item in infos] != sorted(item.filename for item in infos):
            raise ValueError("archive outcome package order changed")
        if {item.filename for item in infos} != expected_names:
            raise ValueError("archive outcome package entry set changed")
        for item in infos:
            pure = PurePosixPath(item.filename)
            if pure.is_absolute() or ".." in pure.parts or item.is_dir():
                raise ValueError(f"unsafe evidence package path: {item.filename}")
            if item.date_time != (1980, 1, 1, 0, 0, 0) or (item.external_attr >> 16) != 0o100444:
                raise ValueError(f"evidence package metadata changed: {item.filename}")

        observed_matching = []
        for record in result["metadata_records"]:
            run = record["run_root"]
            payload = archive.read(f"runs/{run}/step_0001_metadata.json")
            if len(payload) != record["size_bytes"] or sha256_bytes(payload) != record["sha256"]:
                raise ValueError(f"metadata evidence changed: {run}")
            metadata = json.loads(payload)
            if metadata["action_input"]["id"] != record["action_id"]:
                raise ValueError(f"recorded action changed: {run}")
            if record["action_id"] == extraction.TARGET_ACTION:
                observed_matching.append(run)
        if observed_matching != result["matching_run_roots"]:
            raise ValueError("matching-run selection changed")

        predictions = extraction.candidate_predictions()
        if predictions != result["candidate_predictions"]:
            raise ValueError("candidate prediction boundary changed")
        recomputed_observations = []
        recomputed_matches = []
        for outcome in result["outcomes"]:
            run = outcome["run_root"]
            for record in outcome["files"]:
                payload = archive.read(f"runs/{run}/{record['basename']}")
                if len(payload) != record["size_bytes"] or sha256_bytes(payload) != record["sha256"]:
                    raise ValueError(f"outcome evidence changed: {run}/{record['basename']}")
            metadata = json.loads(archive.read(f"runs/{run}/step_0001_metadata.json"))
            status = extraction.STATE_TO_STATUS[metadata["state"]]
            frame_hash = extraction.validate_frame(archive.read(f"runs/{run}/step_0001_final.txt"))
            observation = {"final_frame_sha256": frame_hash, "status": status}
            matches = [candidate for candidate, predicted in predictions.items() if predicted == observation]
            if observation != outcome["observation"] or matches != outcome["matching_candidates"]:
                raise ValueError(f"outcome comparison changed: {run}")
            recomputed_observations.append(json.dumps(observation, sort_keys=True))
            recomputed_matches.append(tuple(matches))

    if not recomputed_observations:
        verdict = "no_matching_recorded_p0_action"
    elif len(set(recomputed_observations)) != 1:
        verdict = "recorded_outcome_inconsistent_across_runs"
    elif len(set(recomputed_matches)) == 1 and len(recomputed_matches[0]) == 1:
        verdict = "separator_outcome_matches_one_candidate"
    else:
        verdict = "separator_outcome_outside_candidate_frontier"
    if verdict != result["gate_verdict"]:
        raise ValueError("archive outcome verdict changed")
    accounting = result["access_accounting"]
    if accounting["step1_metadata_payloads_read"] != 5:
        raise ValueError("metadata access accounting changed")
    if accounting["matching_action_nonmetadata_payloads_read"] != 10 * len(result["matching_run_roots"]):
        raise ValueError("matching payload accounting changed")
    for field in (
        "nonmatching_run_frame_payloads_read",
        "later_step_payloads_read",
        "candidate_processes",
        "oia_processes",
        "model_or_api_calls",
        "real_arc_actions",
    ):
        if accounting[field] != 0:
            raise ValueError(f"archive outcome boundary crossed: {field}")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "gate_verdict": verdict,
                "matching_runs": len(result["matching_run_roots"]),
                "pass": True,
                "target_action": result["target_action"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
