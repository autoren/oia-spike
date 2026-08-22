#!/usr/bin/env python3
"""Verify the frozen Tycho local-Qwen evaluator-package R0 boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "integrations/tycho-kaggle-package"
PROTOCOL = INTEGRATION / "PACKAGE_PROTOCOL.json"
RESULT = INTEGRATION / "PACKAGE_RESULT.json"
FILE_MANIFEST = INTEGRATION / "RUNTIME_BUNDLE_FILE_MANIFEST.json"


def load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} root must be an object")
    return payload


def validate_protocol(path: Path = PROTOCOL) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != "OIA-TYCHO-KAGGLE-PACKAGE-R0-0.1":
        raise ValueError("package protocol schema changed")
    pins = payload.get("source_pins") or {}
    if pins.get("official_starter") != {
        "repository": "https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter.git",
        "commit": "eeb1535404f321d280a8f9194bbc1d7aca5f05fc",
        "tree": "332ff438d9b092c95e58a07eace6194379de06b4",
    }:
        raise ValueError("official starter pin changed")
    llama = pins.get("llama_cpp") or {}
    if (
        llama.get("release") != "b10236"
        or llama.get("commit") != "1464c62d88f699ec9700c8010bbfdbc603a9efd6"
        or llama.get("linux_amd64_manifest_digest")
        != "sha256:faebc1dd2e96e4ab9708e786f16477162ef8f3330d4a4838c371220409870fed"
        or llama.get("cuda_version") != "13.3.0"
    ):
        raise ValueError("llama.cpp runtime pin changed")
    authorized = payload.get("authorized_post_freeze_execution") or {}
    expected_nonzero = {
        "runtime_bundle_builds": 1,
        "clean_container_portability_tests": 1,
    }
    for field, value in authorized.items():
        expected = expected_nonzero.get(field, 0)
        if value != expected:
            raise ValueError(f"package execution boundary changed: {field}")
    contract = payload.get("bundle_contract") or {}
    if (
        contract.get("required_version_output") != "version: 10236 (1464c62d8)"
        or contract.get("allowed_unresolved_shared_libraries") != ["libcuda.so.1"]
        or contract.get("network_during_portability_test") is not False
        or contract.get("bundle_mount_during_portability_test") != "read_only"
        or contract.get("maximum_bundle_bytes") != 5_000_000_000
    ):
        raise ValueError("runtime bundle contract changed")
    blockers = payload.get("known_remaining_blockers") or []
    if not any("run_python" in item and "host mode" in item for item in blockers):
        raise ValueError("sandbox blocker disappeared")
    claims = payload.get("claim_boundary") or {}
    if (
        "Kaggle package readiness" not in claims.get("does_not_support", [])
        or "Track B claims" not in claims.get("does_not_support", [])
    ):
        raise ValueError("package claim boundary broadened")
    if payload.get("status") != "frozen_unexecuted":
        raise ValueError("package prospective status changed")
    return payload


def validate_result(
    result_path: Path = RESULT, manifest_path: Path = FILE_MANIFEST
) -> dict[str, Any]:
    result = load_object(result_path)
    manifest = load_object(manifest_path)
    if result.get("schema_version") != "OIA-TYCHO-KAGGLE-PACKAGE-R0-RESULT-0.1":
        raise ValueError("package result schema changed")
    if result.get("verdict") != (
        "runtime_bundle_qualified_adapter_sandbox_and_throughput_unqualified"
    ):
        raise ValueError("package result verdict changed")
    if manifest.get("schema_version") != "OIA-TYCHO-KAGGLE-RUNTIME-FILES-0.1":
        raise ValueError("runtime file manifest schema changed")
    runtime = result.get("runtime_bundle") or {}
    for field in ("entries_sha256", "file_count", "symlink_count", "total_file_bytes"):
        if runtime.get(field) != manifest.get(field):
            raise ValueError(f"runtime result/manifest mismatch: {field}")
    if int(manifest.get("total_file_bytes", 0)) > 5_000_000_000:
        raise ValueError("runtime bundle exceeds size cap")
    portability = manifest.get("portability_test") or {}
    if (
        "version: 10236 (1464c62d8)" not in portability.get("version_output", "")
        or portability.get("network") != "none"
        or portability.get("root_filesystem") != "read_only"
        or portability.get("bundle_mount") != "read_only"
        or portability.get("unresolved_shared_libraries") != ["libcuda.so.1"]
        or portability.get("user_space_cuda_libraries_resolved_from_bundle") is not True
    ):
        raise ValueError("runtime portability result changed")
    boundaries = result.get("zero_execution_boundaries") or {}
    if not boundaries or any(value != 0 for value in boundaries.values()):
        raise ValueError("package result crossed a zero execution boundary")
    remaining = result.get("remaining_blockers") or []
    if not any("sandbox" in item.lower() for item in remaining):
        raise ValueError("package result omitted sandbox blocker")
    claims = result.get("claim_boundary") or {}
    if claims.get("package_ready") is not False or claims.get("track_b") is not False:
        raise ValueError("package result claim boundary broadened")
    if result.get("status") != "completed":
        raise ValueError("package result status changed")
    return result


def main() -> None:
    validate_protocol()
    if RESULT.exists() or FILE_MANIFEST.exists():
        if not RESULT.exists() or not FILE_MANIFEST.exists():
            raise SystemExit("package result and runtime file manifest must appear together")
        result = validate_result()
        status = result["verdict"]
    else:
        status = "tycho_kaggle_package_r0_frozen_unexecuted"
    print(json.dumps({"status": status}, sort_keys=True))


if __name__ == "__main__":
    main()
