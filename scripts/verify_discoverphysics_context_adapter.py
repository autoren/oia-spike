#!/usr/bin/env python3
"""Verify the execution-free DiscoverPhysics context adapter and optional records."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "integrations/discoverphysics/context_adapter.py"
MANIFEST = ROOT / "integrations/discoverphysics/INTEGRATION_MANIFEST.json"
CONTRACT = ROOT / "integrations/discoverphysics/CONTEXT_ADAPTER_CONTRACT.json"

SPEC = importlib.util.spec_from_file_location(
    "discoverphysics_context_adapter", ADAPTER_PATH
)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def _load_events(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read trace {path}: {exc}") from exc
    if not isinstance(value, list):
        raise ValueError("trace root must be an array")
    return value


def validate_manifest(path: Path = MANIFEST, root: Path = ROOT) -> dict[str, Any]:
    payload = _load_object(path, "integration manifest")
    if payload.get("schema_version") != "OIA-DISCOVERPHYSICS-INTEGRATION-0.1":
        raise ValueError("DiscoverPhysics integration schema changed")
    source = payload.get("source") or {}
    if source.get("commit") != adapter.SOURCE_COMMIT:
        raise ValueError("DiscoverPhysics integration source commit changed")
    if source.get("tree") != adapter.SOURCE_TREE:
        raise ValueError("DiscoverPhysics integration source tree changed")
    parent = payload.get("parent_analysis") or {}
    if parent.get("repository_commit") != (
        "863ea9bd23e029539acb38bedb414a5d9cc8bba2"
    ):
        raise ValueError("parent analysis commit changed")
    if parent.get("document_sha256") != (
        "64db93c90e52c4e443d68846b17a77393a190416037b58fd0a9a9f5a94d542e1"
    ):
        raise ValueError("parent distinguishability document changed")
    if parent.get("panel_sha256") != (
        "122acdbb51f7c6e2f121f165155c0973b10645012c1e77b277597e07ec3d409b"
    ):
        raise ValueError("parent distinguishability panel changed")

    artifacts = payload.get("artifacts") or {}
    if not artifacts:
        raise ValueError("integration manifest has no artifacts")
    for relative, descriptor in artifacts.items():
        artifact = root / relative
        if not artifact.is_file() or artifact.is_symlink():
            raise ValueError(f"integration artifact missing: {relative}")
        if artifact.stat().st_size != descriptor.get("size"):
            raise ValueError(f"integration artifact size mismatch: {relative}")
        if sha256(artifact) != descriptor.get("sha256"):
            raise ValueError(f"integration artifact hash mismatch: {relative}")

    execution = payload.get("execution_boundary") or {}
    if not execution:
        raise ValueError("integration execution boundary missing")
    for field, value in execution.items():
        if value != 0:
            raise ValueError(f"integration crossed execution boundary: {field}")
    claims = payload.get("claim_boundary") or {}
    if claims.get("project_reopening_effect") != "none":
        raise ValueError("integration reopened project work")
    if claims.get("broad_ontology_formation_claim_reopened") is not False:
        raise ValueError("integration broadened the ontology claim")
    if payload.get("status") != "context_adapter_frozen_unexecuted":
        raise ValueError("integration status changed")

    contract_path = root / payload.get("contract", "")
    contract = _load_object(contract_path, "adapter contract")
    adapter.validate_contract(contract)
    if sha256(contract_path) != artifacts[payload["contract"]]["sha256"]:
        raise ValueError("adapter contract is not bound to the artifact manifest")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--pair-left", type=Path)
    parser.add_argument("--pair-right", type=Path)
    parser.add_argument("--commitment-nonce-file", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = validate_manifest()
    contract = _load_object(CONTRACT, "adapter contract")
    if (args.pair_left is None) != (args.pair_right is None):
        raise ValueError("--pair-left and --pair-right must be supplied together")
    if (args.pair_left is None) != (args.commitment_nonce_file is None):
        raise ValueError(
            "--commitment-nonce-file is required exactly when a pair is supplied"
        )
    pair = None
    if args.pair_left is not None and args.pair_right is not None:
        pair = adapter.commit_matched_pair(
            contract,
            _load_object(args.pair_left, "left matched-pair member"),
            _load_object(args.pair_right, "right matched-pair member"),
            args.commitment_nonce_file.read_text(encoding="utf-8").strip(),
        )
    trace = None
    if args.trace is not None:
        trace = adapter.validate_trace(contract, _load_events(args.trace))
    print(
        json.dumps(
            {
                "artifacts": len(manifest["artifacts"]),
                "matched_pair_commitment": pair,
                "project_reopening_effect": "none",
                "status": "discoverphysics_context_adapter_verified",
                "trace_validation": trace,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
