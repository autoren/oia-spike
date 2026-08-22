#!/usr/bin/env python3
"""Independently verify the Track A 005b admission/OIA result when present."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005b"
OUTCOME_ROOT = AUDIT_ROOT / "behavior-outcome"
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
ALLOWED_VERDICTS = {
    "revision_generation_or_calibration_blocker",
    "no_revised_behavioral_divergence",
    "nondeterministic_or_runtime_blocker",
    "revision_frontier_feasible",
    "oia_blocker",
    "revised_separator_selected_pre_step2",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not OUTCOME_ROOT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005b", "status": "preexecution_only"}))
        return
    checksum_path = AUDIT_ROOT / "BEHAVIOR_OUTCOME_SHA256SUMS.txt"
    if not checksum_path.is_file():
        raise ValueError("005b behavior outcome checksum manifest missing")
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005b behavior outcome checksum mismatch: {relative}")
    result = load(OUTCOME_ROOT / "ADMISSION_AND_OIA_RESULT.json")
    verdict = result["gate_verdict"]
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError("unexpected 005b behavior/OIA verdict")
    accounting = result["execution_accounting"]
    for field in (
        "step_2_or_later_payloads_read",
        "network_or_service_calls",
        "model_or_api_calls",
        "credential_uses",
        "private_or_sealed_evaluations",
        "real_arc_actions",
    ):
        if accounting[field] != 0:
            raise ValueError(f"005b behavior boundary crossed: {field}")
    if result["epistemic_ordering"]["selected_next_action_merged_before_step2_access_required"] is not True:
        raise ValueError("005b prospective ordering changed")
    calibration = result["stages"]["calibration"]
    for row in calibration["records"]:
        if row["pass"]:
            trace = row["trace"]
            if (
                trace["p0"]["frame_sha256"]
                != "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
                or trace["calibration"]["final_frame_sha256"]
                != "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"
                or trace["calibration"]["status"] != "RUNNING"
            ):
                raise ValueError("005b exact calibration evidence changed")
    full = result["stages"]["full"]
    if full["seeds"] != [0, 1, 5, 10] or full["repetitions_per_seed"] != 2:
        raise ValueError("005b determinism matrix changed")
    for candidate in full["records"]:
        if candidate["candidate_id"] in full["admitted_candidates"]:
            if candidate["all_words_pass"] is not True or candidate["deterministic"] is not True:
                raise ValueError("005b admitted evidence changed")
        if len(candidate["word_records"]) != 14:
            raise ValueError("005b word coverage changed")
        for word in candidate["word_records"]:
            if len(word["repetitions"]) != 8:
                raise ValueError("005b repetition coverage changed")
    expected_processes = (
        len(calibration["records"])
        + 14
        * sum(1 for row in calibration["records"] if row["pass"])
        + 14 * 8 * len(result["stages"]["provisional"]["provisionally_unique"])
    )
    if accounting["candidate_processes"] != expected_processes:
        raise ValueError("005b candidate process accounting changed")

    if verdict == "revised_separator_selected_pre_step2":
        if len(full["admitted_candidates"]) < 2:
            raise ValueError("005b selected action has insufficient frontier")
        payload_path = OUTCOME_ROOT / "OIA_INPUT.json"
        report_path = OUTCOME_ROOT / "OIA_REPORT.json"
        payload = load(payload_path)
        report = load(report_path)
        if sha256(report_path) != result["oia_report_sha256"]:
            raise ValueError("005b OIA report hash changed")
        if set(result["cross_process_oia_report_sha256"].values()) != {sha256(report_path)}:
            raise ValueError("005b cross-process OIA hashes changed")
        sys.path.insert(0, str(BASELINE_SRC))
        from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

        system = CandidateSystem.from_dict(payload)
        adaptive = report["full_candidate_identification"]["adaptive"]
        depth = verify_serialized_adaptive_result(system, adaptive)
        policy = adaptive.get("policy") or {}
        if (
            adaptive["status"] != "solved"
            or adaptive["exact"] is not True
            or adaptive["enumeration_complete"] is not True
            or adaptive["optimality_certified"] is not True
            or adaptive["depth_claim"] != "minimum"
            or depth != adaptive["worst_case_steps"]
            or policy.get("type") != "action"
            or policy.get("action") != result["selected_next_action"]
        ):
            raise ValueError("005b exact adaptive-policy evidence changed")
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(BASELINE_SRC)
        environment["PYTHONHASHSEED"] = "23"
        with tempfile.TemporaryDirectory(prefix="oia-005b-verify-") as temporary:
            independent = Path(temporary) / "report.json"
            completed = subprocess.run(
                (
                    sys.executable,
                    "-m",
                    "ontology_auditor.cli",
                    str(payload_path),
                    "--output",
                    str(independent),
                ),
                cwd=ROOT,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if completed.stderr or independent.read_bytes() != report_path.read_bytes():
                raise ValueError("005b independent seed-23 OIA report differs")
    print(
        json.dumps(
            {
                "admitted": len(full["admitted_candidates"]),
                "audit_id": "OIA-1-TRACK-A-005b",
                "gate_verdict": verdict,
                "pass": True,
                "selected_next_action": result["selected_next_action"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
