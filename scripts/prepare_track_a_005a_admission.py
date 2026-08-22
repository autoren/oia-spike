#!/usr/bin/env python3
"""Prepare opaque Track A 005a candidates without importing or executing them."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
RESULT_PATH = AUDIT_ROOT / "candidate-generation" / "GENERATION_RESULT.json"
PACKAGE_PATH = AUDIT_ROOT / "candidate-generation" / "CANDIDATE_PACKAGE.zip"
EXPECTED_PACKAGE_SHA256 = "9ae478a842b942bc80f3ff62063e4780d8097018384971d83db12fd6d87b167a"
EXPECTED_CANDIDATES = ("C0006", "C0008")
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
FORBIDDEN_NAMES = {
    "__builtins__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "memoryview",
    "open",
    "setattr",
    "vars",
}
FORBIDDEN_ATTRIBUTES = {
    "ctypes",
    "dump",
    "dumps",
    "fromfile",
    "load",
    "loads",
    "memmap",
    "save",
    "savetxt",
    "tofile",
}

sys.path.insert(0, str(ROOT / "scripts"))
from generate_track_a_005a_candidates import validate_code


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def hardened_static_scan(code: str) -> dict[str, object]:
    baseline = validate_code(code)
    tree = ast.parse(code, mode="exec")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    forbidden_names = sorted(names & FORBIDDEN_NAMES)
    forbidden_attributes = sorted(attributes & FORBIDDEN_ATTRIBUTES)
    if forbidden_names:
        raise ValueError(f"forbidden names: {forbidden_names}")
    if forbidden_attributes:
        raise ValueError(f"forbidden attributes: {forbidden_attributes}")
    return {
        "ast_node_count": baseline["ast_node_count"],
        "functions": baseline["functions"],
        "imports": baseline["imports"],
        "forbidden_attributes": forbidden_attributes,
        "forbidden_names": forbidden_names,
        "result": "pass",
    }


def make_read_only(root: Path) -> None:
    for path in root.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def prepare(destination: Path) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    if sha256_file(PACKAGE_PATH) != EXPECTED_PACKAGE_SHA256:
        raise ValueError("candidate package pin changed")
    generation = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if generation["status"] != "fresh_candidate_generation_feasible":
        raise ValueError("generation gate is not feasible")
    accepted = [
        row
        for row in generation["candidate_records"]
        if row["status"] == "structurally_accepted_not_executed"
    ]
    if tuple(row["candidate_id"] for row in accepted) != EXPECTED_CANDIDATES:
        raise ValueError("accepted candidate identity changed")

    destination.mkdir(parents=True)
    candidate_root = destination / "candidates"
    candidate_root.mkdir()
    p0_root = destination / "p0"
    p0_root.mkdir()
    p0_bytes = (AUDIT_ROOT / "p0" / "initial_frame.txt").read_bytes()
    if sha256_bytes(p0_bytes) != EXPECTED_P0_SHA256:
        raise ValueError("P0 raster pin changed")
    (p0_root / "initial_frame.txt").write_bytes(p0_bytes)
    records: list[dict[str, object]] = []
    with zipfile.ZipFile(PACKAGE_PATH) as archive:
        infos = archive.infolist()
        if len(infos) != len({item.filename for item in infos}):
            raise ValueError("candidate package has duplicate paths")
        if any(
            PurePosixPath(item.filename).is_absolute()
            or ".." in PurePosixPath(item.filename).parts
            for item in infos
        ):
            raise ValueError("candidate package contains an unsafe path")
        manifest = json.loads(archive.read("CANDIDATE_MANIFEST.json"))
        if tuple(row["candidate_id"] for row in manifest["candidates"]) != EXPECTED_CANDIDATES:
            raise ValueError("package candidate order changed")
        for candidate in manifest["candidates"]:
            candidate_id = candidate["candidate_id"]
            source_name = f"candidates/{candidate_id}/candidate.py"
            source = archive.read(source_name)
            if sha256_bytes(source) != candidate["candidate_sha256"]:
                raise ValueError(f"candidate source hash changed: {candidate_id}")
            try:
                scan = hardened_static_scan(source.decode("utf-8"))
            except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
                records.append(
                    {
                        "candidate_id": candidate_id,
                        "candidate_sha256": candidate["candidate_sha256"],
                        "status": "rejected_hardened_static_scan",
                        "reason": f"{type(exc).__name__}:{exc}",
                    }
                )
                continue
            output_dir = candidate_root / candidate_id
            output_dir.mkdir()
            output_path = output_dir / "candidate.py"
            output_path.write_bytes(source)
            records.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_sha256": candidate["candidate_sha256"],
                    "candidate_size_bytes": len(source),
                    "stance_id": candidate["stance_id"],
                    "static_scan": scan,
                    "status": "prepared_not_imported_or_executed",
                }
            )

    prepared = [row for row in records if row["status"] == "prepared_not_imported_or_executed"]
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "status": (
            "candidate_bundles_prepared_behavior_not_run"
            if len(prepared) >= 2
            else "static_admission_blocker"
        ),
        "generation_result_sha256": sha256_file(RESULT_PATH),
        "candidate_package_sha256": EXPECTED_PACKAGE_SHA256,
        "p0_frame_sha256": EXPECTED_P0_SHA256,
        "candidate_records": records,
        "accounting": {
            "source_records_opened": len(accepted),
            "hardened_static_pass": len(prepared),
            "hardened_static_rejected": len(records) - len(prepared),
            "candidate_imports": 0,
            "candidate_processes": 0,
            "candidate_behavior_steps": 0,
            "oia_processes": 0,
            "real_arc_actions": 0,
            "held_out_post_p0_payloads_read": 0,
            "network_or_service_calls": 0,
        },
        "claim_boundary": (
            "Opened candidate-source static admission only; no candidate import, "
            "behavior, OIA execution, or post-P0 held-out outcome access."
        ),
    }
    (destination / "PREPARED_BUNDLES.json").write_bytes(canonical_bytes(result))
    make_read_only(destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.destination.resolve())
    print(
        json.dumps(
            {
                "candidate_imports": result["accounting"]["candidate_imports"],
                "prepared": result["accounting"]["hardened_static_pass"],
                "rejected": result["accounting"]["hardened_static_rejected"],
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
