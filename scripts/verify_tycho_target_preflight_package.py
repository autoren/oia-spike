#!/usr/bin/env python3
"""Verify the frozen Tycho target-preflight R2a package evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations/tycho-target-preflight"
PROTOCOL = BASE / "PREFLIGHT_PACKAGE_PROTOCOL.json"
FREEZE = BASE / "PREFLIGHT_PACKAGE_IMPLEMENTATION_FREEZE.json"
MANIFEST = BASE / "TARGET_BUNDLE_MANIFEST.json"
RESULT = BASE / "PREFLIGHT_PACKAGE_RESULT.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(path: Path = PROTOCOL) -> dict:
    payload = load(path)
    if payload["schema_version"] != "OIA-TYCHO-TARGET-PREFLIGHT-PACKAGE-PROTOCOL-0.1":
        raise ValueError("protocol schema changed")
    execution = payload["authorized_post_freeze_execution"]
    expected_positive = {
        "bundle_builds": 1,
        "independent_manifest_verifications": 1,
        "static_elf_inspections": 1,
    }
    if {key: execution.get(key) for key in expected_positive} != expected_positive:
        raise ValueError("package execution allowance changed")
    expected_zero = {
        "x86_64_sandlock_executions",
        "target_notebook_runs",
        "kaggle_uploads",
        "credentials",
        "model_loads",
        "model_calls",
        "gpu_runs",
        "arc_actions",
        "oia_runs",
        "submissions",
        "hidden_games",
    }
    if any(execution.get(key) != 0 for key in expected_zero):
        raise ValueError("forbidden execution boundary changed")
    runner = payload["bundle_contract"]["target_runner"]
    if runner["host_fallback"] or runner["loads_model"] or runner["starts_arc"] or runner["runs_oia"]:
        raise ValueError("target runner boundary changed")
    return payload


def validate_freeze(path: Path = FREEZE) -> dict:
    payload = load(path)
    expected = {PROTOCOL: payload["protocol"]["sha256"]}
    for item in payload["implementation"]:
        expected[ROOT / item["path"]] = item["sha256"]
    for artifact, digest in expected.items():
        if sha256(artifact) != digest:
            raise ValueError(f"frozen implementation changed: {artifact.name}")
    return payload


def validate_manifest(path: Path = MANIFEST) -> dict:
    payload = load(path)
    if payload["schema_version"] != "OIA-TYCHO-TARGET-PREFLIGHT-BUNDLE-0.1":
        raise ValueError("bundle manifest schema changed")
    entries = payload["entries"]
    if len(entries) != 76:
        raise ValueError("bundle entry count changed")
    paths = [entry["path"] for entry in entries]
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        raise ValueError("bundle paths are not unique and sorted")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != payload["entries_sha256"]:
        raise ValueError("bundle canonical entry hash changed")
    if payload["entries_sha256"] != (
        "cac135dace6772d041b539a589baf65377a74893f2494654a0b91794f90bf1b4"
    ):
        raise ValueError("bundle entry set changed")
    by_path = {entry["path"]: entry for entry in entries}
    required = {
        "bin/sandlock": (12204192, "86f80d68afe0146287ee9b950ca0223945fe49e8722f6c80ffb89eb623e53b27", 0o755),
        "source/sandlock-x86_64-v0.8.6.tar.gz": (11424640, "86e89e5bdb2da748e683cda6908a95504ae6751f73d9dadf79cf0fc6843873fb", 0o644),
        "source/tycho-f68912a.tar.gz": (387769, "c82c8dde62109ead0c67716a54b107bd060791ce5fd00d9123067e07d0ef6018", 0o644),
        "source/sandlock-python-sandbox-v0.1.patch": (12881, "a4f657e3e5cb0759bcab527d834eae169f5f704063109967d06acb5473aa78c8", 0o644),
        "run_target_preflight.py": (sha256(ROOT / "scripts/run_tycho_target_preflight.py"),),
        "verify_offline_bundle.py": (sha256(ROOT / "scripts/verify_offline_tycho_target_preflight.py"),),
    }
    for name, expected in required.items():
        if name not in by_path:
            raise ValueError(f"required bundle path missing: {name}")
        entry = by_path[name]
        if len(expected) == 1:
            if entry["sha256"] != expected[0]:
                raise ValueError(f"required bundle file changed: {name}")
        elif (entry["bytes"], entry["sha256"], entry["mode"]) != expected:
            raise ValueError(f"required bundle file changed: {name}")
    return payload


def validate_result(path: Path = RESULT) -> dict:
    payload = load(path)
    if payload["verdict"] != "offline_target_preflight_bundle_ready_target_execution_pending":
        raise ValueError("package verdict changed")
    protocol = validate_protocol()["authorized_post_freeze_execution"]
    accounting = payload["execution_accounting"]
    if any(accounting.get(key) != value for key, value in protocol.items()):
        raise ValueError("package execution accounting changed")
    build = payload["build"]
    if build["entry_count"] != 76 or build["zip_bytes"] > 20_000_000:
        raise ValueError("package size or entry count changed")
    if build["zip_sha256"] != "21f530d5262858583224f9c0ee1638765da547e521875b8a31bfe446143f731e":
        raise ValueError("package ZIP hash changed")
    if payload["artifact_hashes"]["tracked_bundle_manifest_sha256"] != sha256(MANIFEST):
        raise ValueError("tracked bundle manifest hash changed")
    claims = payload["claim_boundary"]
    if not claims["offline_preflight_bundle_reproducible"]:
        raise ValueError("package claim changed")
    forbidden_true = {
        "target_kernel_support",
        "x86_64_sandlock_execution",
        "kaggle_upload_or_notebook_run",
        "myagent_adapter",
        "model_gpu_load",
        "throughput",
        "arc_behavior_or_progress",
        "oia_discovery_or_transfer",
        "submission_or_hidden_evaluation",
    }
    if any(claims[key] for key in forbidden_true):
        raise ValueError("package claim boundary broadened")
    return payload


def main() -> None:
    validate_protocol()
    validate_freeze()
    manifest = validate_manifest()
    result = validate_result()
    print(
        json.dumps(
            {
                "entry_count": len(manifest["entries"]),
                "gate_id": result["gate_id"],
                "status": "verified",
                "verdict": result["verdict"],
                "zip_sha256": result["build"]["zip_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
