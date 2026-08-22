#!/usr/bin/env python3
"""Verify the post-freeze DiscoverPhysics context-adapter qualification result."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FREEZE_VERIFIER_PATH = ROOT / "scripts/verify_discoverphysics_context_adapter.py"
RESULT = ROOT / "integrations/discoverphysics/INTEGRATION_RESULT.json"
REPORT = ROOT / "integrations/discoverphysics/QUALIFICATION_REPORT.md"

SPEC = importlib.util.spec_from_file_location(
    "verify_discoverphysics_context_adapter", FREEZE_VERIFIER_PATH
)
assert SPEC is not None and SPEC.loader is not None
freeze_verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = freeze_verifier
SPEC.loader.exec_module(freeze_verifier)


def validate_result(path: Path = RESULT, root: Path = ROOT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != (
        "OIA-DISCOVERPHYSICS-INTEGRATION-RESULT-0.1"
    ):
        raise ValueError("DiscoverPhysics qualification-result schema changed")
    if payload.get("protocol_freeze_commit") != (
        "567ea6760881d940b150dcb66e1052648d15d69a"
    ):
        raise ValueError("context-adapter prospective ordering changed")
    protocol = payload.get("protocol_manifest") or {}
    protocol_path = root / protocol.get("path", "")
    if freeze_verifier.sha256(protocol_path) != protocol.get("sha256"):
        raise ValueError("frozen protocol manifest changed")
    freeze_verifier.validate_manifest(protocol_path, root)

    report = payload.get("qualification_report") or {}
    report_path = root / report.get("path", "")
    if not report_path.is_file() or report_path.is_symlink():
        raise ValueError("qualification report missing")
    if report_path.stat().st_size != report.get("size"):
        raise ValueError("qualification report size changed")
    if freeze_verifier.sha256(report_path) != report.get("sha256"):
        raise ValueError("qualification report hash changed")

    attempts = payload.get("attempts") or []
    if (
        len(attempts) != 3
        or attempts[0].get("standalone_tests_passed") != 84
        or attempts[0].get("baseline_tests_passed") != 1
        or attempts[0].get("baseline_test_import_errors") != 2
        or attempts[0].get("failure_class") != "test_environment_import_path_missing"
        or attempts[0].get("exit_code") != 1
        or attempts[0].get("boundary_crossed") is not False
        or attempts[1].get("baseline_tests_passed") != 23
        or attempts[1].get("baseline_tests_failed") != 0
        or attempts[1].get("baseline_provenance_verifier") != "pass"
        or attempts[1].get("exit_code") != 0
        or attempts[1].get("boundary_crossed") is not False
        or attempts[2].get("standalone_head")
        != "567ea6760881d940b150dcb66e1052648d15d69a"
        or attempts[2].get("external_verifiers_passed") != 4
        or attempts[2].get("exit_code") != 0
        or attempts[2].get("boundary_crossed") is not False
    ):
        raise ValueError("qualification attempt accounting changed")

    capabilities = payload.get("validated_capabilities") or {}
    expected_capabilities = {
        "frozen_artifacts_verified": 4,
        "standalone_tests_passed": 84,
        "maintained_historical_freezes_verified": 4,
        "baseline_tests_passed": 23,
        "baseline_provenance_verifier": "pass",
        "parent_cross_repository_verifier": "pass",
        "context_complete_candidate_call": "pass",
        "time_blind_upstream_signature_rejected": "pass",
        "single_change_matched_pair_validation": "pass",
        "nonce_hardened_hiding_commitment": "pass",
        "private_truth_rejection": "pass",
        "strict_trace_order_and_context_linkage": "pass",
    }
    if capabilities != expected_capabilities:
        raise ValueError("validated capability accounting changed")

    for field, value in (payload.get("execution_accounting") or {}).items():
        if value != 0:
            raise ValueError(f"qualification crossed execution boundary: {field}")
    if payload.get("verdict") != (
        "credential_free_context_adapter_qualification_pass"
    ):
        raise ValueError("qualification verdict changed")
    if payload.get("next_empirical_gate") is not None:
        raise ValueError("qualification opened an empirical gate")
    if payload.get("project_reopening_effect") != "none":
        raise ValueError("qualification reopened project work")
    return payload


def main() -> None:
    result = validate_result()
    print(
        json.dumps(
            {
                "project_reopening_effect": result["project_reopening_effect"],
                "status": "discoverphysics_context_adapter_result_verified",
                "verdict": result["verdict"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
