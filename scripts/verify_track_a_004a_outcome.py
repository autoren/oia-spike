#!/usr/bin/env python3
"""Independently verify the Track A 004a outcome when present."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-004a"
OUTCOME_ROOT = AUDIT_ROOT / "outcome"
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not OUTCOME_ROOT.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-004a", "status": "pre_run_only"}))
        return

    manifest = load_json(OUTCOME_ROOT / "PACKAGE_MANIFEST.json")
    if manifest["gate_verdict"] != "retrospective_instrument_validation_pass":
        raise ValueError("unexpected outcome verdict")
    for record in manifest["files"]:
        path = OUTCOME_ROOT / record["path"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"invalid outcome path: {record['path']}")
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"outcome file mismatch: {record['path']}")
    if manifest["pre_run_manifest_sha256"] != sha256(AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt"):
        raise ValueError("pre-run package pin changed")

    for line in (OUTCOME_ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if sha256(OUTCOME_ROOT / name) != digest:
            raise ValueError(f"outcome checksum mismatch: {name}")

    payload = load_json(AUDIT_ROOT / "OIA_INPUT.frozen.json")
    report = load_json(OUTCOME_ROOT / "OIA_REPORT.json")
    execution = load_json(OUTCOME_ROOT / "EXECUTION_RECORD.json")
    replay = load_json(OUTCOME_ROOT / "POLICY_REPLAY.json")

    sys.path.insert(0, str(BASELINE_SRC))
    from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

    system = CandidateSystem.from_dict(payload)
    adaptive = report["full_candidate_identification"]["adaptive"]
    depth = verify_serialized_adaptive_result(system, adaptive)
    if depth != 1 or execution["verified_worst_case_steps"] != depth:
        raise ValueError("verified policy depth changed")
    if adaptive["status"] != "solved" or adaptive["optimality_certified"] is not True:
        raise ValueError("exact OIA certificate changed")
    if report["pairwise_separation"] != [
        {
            "distinguishable": True,
            "left": "C0001",
            "right": "C0002",
            "sequence": ["ACTION2"],
        }
    ]:
        raise ValueError("pairwise separator changed")
    if replay["all_paths_valid"] is not True or replay["maximum_steps"] != 1:
        raise ValueError("source-trace policy replay changed")
    accounting = execution["execution_accounting"]
    for field in (
        "candidate_processes",
        "real_arc_actions",
        "network_or_service_calls",
        "credential_uses",
        "model_or_api_calls",
        "private_or_sealed_evaluations",
    ):
        if accounting[field] != 0:
            raise ValueError(f"claim boundary crossed: {field}")

    expected_report_sha = sha256(OUTCOME_ROOT / "OIA_REPORT.json")
    hashes = execution["cross_process_serialization"]["report_sha256_by_seed"]
    if set(hashes.values()) != {expected_report_sha}:
        raise ValueError("recorded cross-process report hashes disagree")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(BASELINE_SRC)
    with tempfile.TemporaryDirectory(prefix="oia-004a-verify-") as temporary:
        report_path = Path(temporary) / "report.json"
        environment["PYTHONHASHSEED"] = "23"
        subprocess.run(
            (
                sys.executable,
                "-m",
                "ontology_auditor.cli",
                str(AUDIT_ROOT / "OIA_INPUT.frozen.json"),
                "--output",
                str(report_path),
            ),
            cwd=ROOT,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if report_path.read_bytes() != (OUTCOME_ROOT / "OIA_REPORT.json").read_bytes():
            raise ValueError("independent seed-23 OIA report differs")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-004a",
                "gate_verdict": execution["gate_verdict"],
                "independent_seed": 23,
                "minimum_separator": execution["minimum_separator"],
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
