#!/usr/bin/env python3
"""Verify immutable files and claim boundaries for the Tycho trace integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "integrations/tycho/INTEGRATION_MANIFEST.json"
RESULT = ROOT / "integrations/tycho/INTEGRATION_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(path: Path = MANIFEST, root: Path = ROOT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "OIA-TYCHO-TRACE-INTEGRATION-0.1":
        raise ValueError("Tycho trace-integration schema changed")
    source = payload.get("source") or {}
    if source.get("commit") != "f68912a764372ead0a610db2e1c011d41ce5197e":
        raise ValueError("Tycho integration source commit changed")
    if source.get("tree") != "d5ff6a4e142934ceb865e403e3aa92d80bfa245c":
        raise ValueError("Tycho integration source tree changed")
    for rel, descriptor in (payload.get("artifacts") or {}).items():
        artifact = root / rel
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError(f"Tycho integration artifact missing: {rel}")
        if artifact.stat().st_size != descriptor.get("size"):
            raise ValueError(f"Tycho integration artifact size mismatch: {rel}")
        if sha256(artifact) != descriptor.get("sha256"):
            raise ValueError(f"Tycho integration artifact hash mismatch: {rel}")
    execution = payload.get("execution_boundary") or {}
    for field in (
        "model_calls_authorized",
        "service_calls_authorized",
        "arc_actions_authorized",
        "environment_resets_authorized",
        "private_payloads_authorized",
    ):
        if execution.get(field) != 0:
            raise ValueError(f"Tycho integration crossed execution boundary: {field}")
    claims = payload.get("claim_boundary") or {}
    if claims.get("project_reopening_effect") != "none":
        raise ValueError("Tycho integration changed project reopening state")
    if claims.get("broad_ontology_formation_claim_reopened") is not False:
        raise ValueError("Tycho integration broadened the claim")
    return payload


def validate_result(path: Path = RESULT) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "OIA-TYCHO-TRACE-INTEGRATION-RESULT-0.1":
        raise ValueError("Tycho trace-integration result schema changed")
    if payload.get("protocol_freeze_commit") != "20f40caacad89b5518f8b92a59cb083ce5841b2e":
        raise ValueError("Tycho integration prospective ordering changed")
    if payload.get("patch", {}).get("sha256") != (
        "804db588cce430242035c1d26e4f8f19bc214a3cacdfae277153dbeac5cdc27c"
    ):
        raise ValueError("Tycho integration result patch changed")
    attempts = payload.get("attempts") or []
    if (
        len(attempts) != 2
        or attempts[0].get("tycho_tests_executed") != 0
        or attempts[0].get("boundary_crossed") is not False
        or attempts[1].get("tycho_tests_passed") != 164
        or attempts[1].get("tycho_tests_failed") != 0
        or attempts[1].get("exit_code") != 0
    ):
        raise ValueError("Tycho integration attempt accounting changed")
    for field, value in (payload.get("execution_accounting") or {}).items():
        if value != 0:
            raise ValueError(f"Tycho integration result crossed boundary: {field}")
    if payload.get("verdict") != "credential_free_logging_integration_pass":
        raise ValueError("Tycho integration result verdict changed")
    if payload.get("project_reopening_effect") != "none":
        raise ValueError("Tycho integration result reopened project work")
    return payload


def main() -> None:
    payload = validate_manifest()
    result = validate_result()
    print(
        json.dumps(
            {
                "status": "tycho_trace_integration_verified",
                "artifacts": len(payload["artifacts"]),
                "qualification_verdict": result["verdict"],
                "project_reopening_effect": "none",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
