#!/usr/bin/env python3
"""Run unchanged exact admission/OIA on maintenance-normalized candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
sys.path.insert(0, str(ROOT / "scripts"))
import run_track_a_005b_admission_and_oia as run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    args = parser.parse_args()

    prepared_root = args.prepared_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"outcome root exists: {output_root}")
    image_id = run.docker_image_id(args.image)
    if image_id != args.expected_image_id:
        raise ValueError("runtime image ID changed")
    prepared, candidates = run.load_prepared(prepared_root)
    if prepared["audit_id"] != "OIA-1-TRACK-A-005c":
        raise ValueError("prepared maintenance audit changed")
    output_root.mkdir(parents=True)
    accounting = {
        "candidate_processes": 0,
        "oia_processes": 0,
        "step_2_or_later_payloads_read": 0,
        "network_or_service_calls": 0,
        "model_or_api_calls": 0,
        "credential_uses": 0,
        "private_or_sealed_evaluations": 0,
        "real_arc_actions": 0,
    }
    calibration = run.calibration_stage(
        args.image, prepared_root, candidates, args.timeout_seconds, accounting
    )
    provisional = run.provisional_stage(
        args.image,
        prepared_root,
        candidates,
        calibration,
        args.timeout_seconds,
        accounting,
    )
    full = run.full_stage(
        args.image,
        prepared_root,
        candidates,
        provisional,
        args.timeout_seconds,
        accounting,
    )
    verdict = run.blocker_verdict(calibration, provisional, full)
    adapter_validation = None
    selected_next_action = None
    adaptive_depth = None
    oia_hashes = None
    oia_report_sha256 = None
    if verdict == "revision_frontier_feasible":
        payload, adapter_validation = run.base.build_adapter(full)
        payload_path = output_root / "OIA_INPUT.json"
        payload_path.write_bytes(run.pretty_bytes(payload))
        report_bytes, oia_hashes = run.base.run_oia(payload_path, accounting)
        report = json.loads(report_bytes)
        sys.path.insert(0, str(BASELINE_SRC))
        from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

        system = CandidateSystem.from_dict(payload)
        adaptive = report["full_candidate_identification"]["adaptive"]
        try:
            adaptive_depth = verify_serialized_adaptive_result(system, adaptive)
        except Exception:
            verdict = "oia_blocker"
        else:
            policy = adaptive.get("policy") or {}
            if (
                adaptive.get("status") != "solved"
                or adaptive.get("exact") is not True
                or adaptive.get("enumeration_complete") is not True
                or adaptive.get("optimality_certified") is not True
                or adaptive.get("depth_claim") != "minimum"
                or policy.get("type") != "action"
                or policy.get("action") not in run.ACTIONS
                or adaptive_depth != adaptive.get("worst_case_steps")
            ):
                verdict = "oia_blocker"
            else:
                selected_next_action = policy["action"]
                verdict = "maintenance_revised_separator_selected_pre_step2"
        (output_root / "OIA_REPORT.json").write_bytes(report_bytes)
        (output_root / "ADAPTER_VALIDATION.json").write_bytes(
            run.pretty_bytes(adapter_validation)
        )
        oia_report_sha256 = run.sha256_bytes(report_bytes)

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005c",
        "parent_audit_id": "OIA-1-TRACK-A-005b",
        "maintenance": "prepend import copy only under frozen AST preconditions",
        "gate_verdict": verdict,
        "runtime_image_id": image_id,
        "prepared_bundles_sha256": run.sha256_file(
            prepared_root / "PREPARED_BUNDLES.json"
        ),
        "stages": {
            "calibration": calibration,
            "provisional": provisional,
            "full": full,
        },
        "adapter_validation": adapter_validation,
        "selected_next_action": selected_next_action,
        "adaptive_minimum_worst_case_depth": adaptive_depth,
        "oia_report_sha256": oia_report_sha256,
        "cross_process_oia_report_sha256": oia_hashes,
        "p1_persistence_baseline": {
            "definition": "Predict exact settled P1 and RUNNING after every next action.",
            "p1_sha256": run.EXPECTED_P1_SHA256,
            "evaluated_against_step2": False,
        },
        "execution_accounting": accounting,
        "epistemic_ordering": {
            "maintenance_rules_merged_before_normalization": True,
            "normalized_package_merged_before_execution": True,
            "selected_next_action_merged_before_step2_access_required": True,
            "step_2_or_later_payloads_read": 0,
        },
        "claim_boundary": (
            "Opened Track A exact calibration/admission/OIA on deterministically "
            "missing-import-normalized candidates. This is not untouched-model-output "
            "evidence; no step-2 outcome, real ARC action, sealed transfer, or Track B claim."
        ),
    }
    result_path = output_root / "ADMISSION_AND_OIA_RESULT.json"
    result_path.write_bytes(run.pretty_bytes(result))
    print(
        json.dumps(
            {
                "admitted": len(full["admitted_candidates"]),
                "candidate_processes": accounting["candidate_processes"],
                "gate_verdict": verdict,
                "oia_processes": accounting["oia_processes"],
                "selected_next_action": selected_next_action,
                "result_sha256": run.sha256_file(result_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
