#!/usr/bin/env python3
"""Independently verify the Track A 005a behavior/OIA outcome when present."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
OUTCOME_ROOT = AUDIT_ROOT / "behavior-outcome"
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
ALLOWED_VERDICTS = {
    "prospective_separator_selected_pre_outcome",
    "static_admission_blocker",
    "replay_failure",
    "no_behavioral_divergence",
    "nondeterministic_or_runtime_blocker",
    "oia_blocker",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not OUTCOME_ROOT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005a", "status": "preexecution_only"}))
        return
    manifest = AUDIT_ROOT / "BEHAVIOR_OUTCOME_SHA256SUMS.txt"
    if not manifest.is_file():
        raise ValueError("behavior outcome checksum manifest missing")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"behavior outcome checksum mismatch: {relative}")

    result = load(OUTCOME_ROOT / "ADMISSION_AND_OIA_RESULT.json")
    verdict = result["gate_verdict"]
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError("unexpected behavior/OIA verdict")
    accounting = result["execution_accounting"]
    for field in (
        "real_arc_actions",
        "held_out_post_p0_payloads_read",
        "network_or_service_calls",
        "model_or_api_calls",
        "credential_uses",
        "private_or_sealed_evaluations",
    ):
        if accounting[field] != 0:
            raise ValueError(f"behavior outcome boundary crossed: {field}")
    if result["epistemic_ordering"]["oia_separator_selected_before_held_out_post_p0_outcome"] is not True:
        raise ValueError("prospective ordering changed")

    if verdict == "prospective_separator_selected_pre_outcome":
        full = result["stages"]["full"]
        if full["admitted_candidates"] != ["C0006", "C0008"]:
            raise ValueError("admitted candidate frontier changed")
        if full["seeds"] != [0, 1, 5, 10] or full["repetitions_per_seed"] != 2:
            raise ValueError("determinism matrix changed")
        if accounting["candidate_processes"] != 254 or accounting["oia_processes"] != 4:
            raise ValueError("execution accounting changed")
        for candidate in full["records"]:
            if candidate["all_words_pass"] is not True or candidate["deterministic"] is not True:
                raise ValueError("admitted candidate evidence changed")
            if len(candidate["word_records"]) != 14:
                raise ValueError("candidate word coverage changed")
            for word in candidate["word_records"]:
                if word["deterministic"] is not True or len(word["repetitions"]) != 8:
                    raise ValueError("candidate repetition evidence changed")

        payload_path = OUTCOME_ROOT / "OIA_INPUT.json"
        report_path = OUTCOME_ROOT / "OIA_REPORT.json"
        payload = load(payload_path)
        report = load(report_path)
        if sha256(report_path) != result["oia_report_sha256"]:
            raise ValueError("OIA report hash changed")
        if set(result["cross_process_oia_report_sha256"].values()) != {sha256(report_path)}:
            raise ValueError("cross-process OIA report hashes changed")
        sys.path.insert(0, str(BASELINE_SRC))
        from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

        system = CandidateSystem.from_dict(payload)
        adaptive = report["full_candidate_identification"]["adaptive"]
        depth = verify_serialized_adaptive_result(system, adaptive)
        separator = result["minimum_separator"]
        if (
            adaptive["status"] != "solved"
            or adaptive["exact"] is not True
            or adaptive["optimality_certified"] is not True
            or depth != len(separator)
            or report["pairwise_separation"][0]["sequence"] != separator
        ):
            raise ValueError("exact OIA separator evidence changed")

        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(BASELINE_SRC)
        environment["PYTHONHASHSEED"] = "23"
        with tempfile.TemporaryDirectory(prefix="oia-005a-verify-") as temporary:
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
                raise ValueError("independent seed-23 OIA report differs")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "gate_verdict": verdict,
                "minimum_separator": result["minimum_separator"],
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
