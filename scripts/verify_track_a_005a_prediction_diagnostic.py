#!/usr/bin/env python3
"""Verify the Track A 005a prediction-error diagnostic when present."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
RESULT = AUDIT_ROOT / "prediction-diagnostic" / "PREDICTION_ERROR_DIAGNOSTIC.json"

sys.path.insert(0, str(ROOT / "scripts"))
import run_track_a_005a_prediction_diagnostic as diagnostic


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not RESULT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005a", "status": "diagnostic_unrun"}))
        return
    manifest = AUDIT_ROOT / "PREDICTION_DIAGNOSTIC_SHA256SUMS.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"prediction diagnostic checksum mismatch: {relative}")
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result["classification"] != "post_outcome_retrospective_error_diagnostic":
        raise ValueError("prediction diagnostic classification changed")
    archive_result = json.loads(
        (AUDIT_ROOT / "archive-outcome" / "ARCHIVE_OUTCOME_RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    run_root = archive_result["matching_run_roots"][0]
    with zipfile.ZipFile(AUDIT_ROOT / "archive-outcome" / "ARCHIVE_OUTCOME_EVIDENCE.zip") as archive:
        actual_rows = diagnostic.frame_rows(
            archive.read(f"runs/{run_root}/step_0001_final.txt")
        )
    p0_rows = diagnostic.frame_rows((AUDIT_ROOT / "p0" / "initial_frame.txt").read_bytes())
    if result["persistence_baseline"] != diagnostic.descriptive_metrics(
        p0_rows=p0_rows, predicted_rows=p0_rows, actual_rows=actual_rows
    ):
        raise ValueError("persistence baseline metrics changed")
    for record in result["candidate_records"]:
        rows = record["final_frame_rows"]
        payload = ("\n".join(rows) + "\n").encode("ascii")
        if hashlib.sha256(payload).hexdigest() != record["predicted_frame_sha256"]:
            raise ValueError(f"candidate diagnostic frame hash changed: {record['candidate_id']}")
        recomputed = diagnostic.descriptive_metrics(
            p0_rows=p0_rows, predicted_rows=rows, actual_rows=actual_rows
        )
        if recomputed != record["metrics"] or record["cross_seed_exact"] is not True:
            raise ValueError(f"candidate diagnostic metrics changed: {record['candidate_id']}")
    accounting = result["execution_accounting"]
    if accounting["candidate_processes"] != 8:
        raise ValueError("prediction diagnostic process accounting changed")
    for field in (
        "oia_processes",
        "real_arc_actions",
        "later_step_payloads_read",
        "model_or_api_calls",
        "network_or_service_calls",
    ):
        if accounting[field] != 0:
            raise ValueError(f"prediction diagnostic boundary crossed: {field}")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "candidate_pixel_mismatch": {
                    row["candidate_id"]: row["metrics"]["pixel_mismatch_count"]
                    for row in result["candidate_records"]
                },
                "pass": True,
                "persistence_pixel_mismatch": result["persistence_baseline"]["pixel_mismatch_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
