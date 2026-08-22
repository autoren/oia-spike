#!/usr/bin/env python3
"""Build hash-verified minimal candidate bundles without importing candidate code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "audits" / "track-a-003b" / "CHECKPOINT_INVENTORY.json"
PROTOCOL_PATH = ROOT / "audits" / "track-a-003b" / "LOCAL_ADMISSION_PROTOCOL.frozen.json"
CANDIDATE_FILES = ("game_status.py", "world_model_engine.py", "world_model_state_io.py")
P0_FILES = ("initial_frame.png", "initial_frame.txt", "initial_metadata.json")
FORBIDDEN_IMPORTS = {
    "anthropic",
    "httpx",
    "openai",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def git_bytes(root: Path, commit: str, path: str) -> bytes:
    result = subprocess.run(
        (
            "git",
            f"--git-dir={root / '.git'}",
            f"--work-tree={root}",
            "show",
            f"{commit}:{path}",
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def static_scan(files: dict[str, bytes]) -> dict:
    imports: set[str] = set()
    literal_paths: set[str] = set()
    for name, data in files.items():
        tree = ast.parse(data.decode("utf-8"), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "with_name" and node.args:
                    argument = node.args[0]
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                        literal_paths.add(argument.value)
    forbidden = sorted(imports & FORBIDDEN_IMPORTS)
    if forbidden:
        raise ValueError(f"forbidden static imports: {forbidden}")
    return {
        "top_level_imports": sorted(imports),
        "forbidden_imports": forbidden,
        "literal_with_name_paths_not_bundled": sorted(literal_paths),
        "candidate_code_imported": False,
    }


def make_read_only(root: Path) -> None:
    for path in root.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def run_roots(payload_root: Path) -> dict[str, Path]:
    base = payload_root / "selected" / "runs_additional"
    return {
        "max": base
        / "ewma_v1.6_sv_gpt-5.6-sol_max_run1"
        / "ls20"
        / "run"
        / "agent_run",
        "xhigh": base
        / "ewma_v1.6_sv_gpt-5.6-sol_xhigh_run1"
        / "ls20"
        / "run"
        / "agent_run",
    }


def candidate_records(inventory: dict) -> list[dict]:
    by_run = {run["short_id"]: run for run in inventory["runs"]}
    records: list[dict] = []
    for short_id in ("max", "xhigh"):
        run = by_run[short_id]
        records.append(
            {
                "candidate_id": f"{short_id}/final",
                "short_id": short_id,
                "kind": "final_worktree",
                "identity": run["final_worktree"]["tree_sha256_excluding_dot_git"],
                "expected_hashes": run["final_worktree"]["core"]["core_file_sha256"],
            }
        )
    for ordered in inventory["candidate_order"]["retained_checkpoints_round_robin"]:
        short_id = ordered["candidate_id"].split("/", 1)[0]
        run = by_run[short_id]
        checkpoint = next(
            item
            for item in run["retained_checkpoints"]
            if item["commit"] == ordered["commit"]
        )
        records.append(
            {
                "candidate_id": ordered["candidate_id"],
                "short_id": short_id,
                "kind": "git_checkpoint",
                "identity": ordered["commit"],
                "tree": ordered["tree"],
                "expected_hashes": checkpoint["core"]["core_file_sha256"],
            }
        )
    return records


def prepare(payload_root: Path, destination: Path) -> dict:
    if destination.exists():
        raise ValueError(f"destination already exists: {destination}")
    inventory_bytes = INVENTORY_PATH.read_bytes()
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if sha256_bytes(inventory_bytes) != protocol["source_inventory"]["sha256"]:
        raise ValueError("inventory does not match the frozen protocol")
    inventory = json.loads(inventory_bytes)
    roots = run_roots(payload_root)
    if any(not root.is_dir() for root in roots.values()):
        raise ValueError("an acquired run root is missing")

    destination.mkdir(parents=True)
    p0_dir = destination / "p0"
    bundles_dir = destination / "candidates"
    p0_dir.mkdir()
    bundles_dir.mkdir()

    canonical_root = roots["max"]
    canonical_p0_dir = canonical_root / "client" / "session" / "level_01_attempt_01"
    p0_hashes: dict[str, str] = {}
    for name in P0_FILES:
        data = (canonical_p0_dir / name).read_bytes()
        observed = sha256_bytes(data)
        expected = protocol["opened_prefix"][
            {
                "initial_frame.png": "initial_frame_png_sha256",
                "initial_frame.txt": "initial_frame_txt_sha256",
                "initial_metadata.json": "initial_metadata_sha256",
            }[name]
        ]
        if observed != expected:
            raise ValueError(f"P0 hash mismatch: {name}")
        (p0_dir / name).write_bytes(data)
        p0_hashes[name] = observed

    manifests: list[dict] = []
    for position, record in enumerate(candidate_records(inventory), start=1):
        bundle_id = f"{position:02d}-{record['candidate_id'].replace('/', '-')}"
        bundle_dir = bundles_dir / bundle_id
        bundle_dir.mkdir()
        root = roots[record["short_id"]]
        files: dict[str, bytes] = {}
        for name in CANDIDATE_FILES:
            if record["kind"] == "final_worktree":
                data = (root / name).read_bytes()
            else:
                data = git_bytes(root, record["identity"], name)
            expected = record["expected_hashes"][name]
            if sha256_bytes(data) != expected:
                raise ValueError(f"candidate hash mismatch: {record['candidate_id']}:{name}")
            (bundle_dir / name).write_bytes(data)
            files[name] = data

        manifest = {
            "schema_version": 1,
            "position": position,
            "bundle_id": bundle_id,
            "candidate_id": record["candidate_id"],
            "kind": record["kind"],
            "source_identity": record["identity"],
            "source_tree": record.get("tree"),
            "files": {
                name: {"size_bytes": len(data), "sha256": sha256_bytes(data)}
                for name, data in sorted(files.items())
            },
            "static_scan": static_scan(files),
            "excluded_session_and_post_p0_state": True,
            "candidate_code_executed": False,
        }
        manifest_bytes = canonical_bytes(manifest)
        (bundle_dir / "BUNDLE_MANIFEST.json").write_bytes(manifest_bytes)
        manifests.append({**manifest, "manifest_sha256": sha256_bytes(manifest_bytes)})

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "status": "candidate_bundles_prepared_behavior_not_run",
        "inventory_sha256": sha256_bytes(inventory_bytes),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "p0": {"directory": "p0", "files": p0_hashes},
        "candidate_count": len(manifests),
        "candidates": manifests,
        "execution_boundary": {
            "candidate_execution": False,
            "arc_execution": False,
            "network_or_service_call": False,
            "credential_use": False,
            "model_or_api_call": False,
            "oia_separability": False,
        },
    }
    result_bytes = canonical_bytes(result)
    (destination / "PREPARED_BUNDLES.json").write_bytes(result_bytes)
    make_read_only(destination)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload_root", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = prepare(args.payload_root.resolve(), args.destination.resolve())
    print(
        json.dumps(
            {
                "candidate_count": result["candidate_count"],
                "candidate_execution": result["execution_boundary"]["candidate_execution"],
                "destination": str(args.destination),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
