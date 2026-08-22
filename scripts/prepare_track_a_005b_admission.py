#!/usr/bin/env python3
"""Prepare opaque revision candidates after their package is independently merged."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "audits" / "track-a-005b" / "revision-input"
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
EXPECTED_P1_SHA256 = "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"
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


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def hardened_static_scan(code: str) -> dict[str, object]:
    baseline = validate_code(code)
    tree = ast.parse(code, mode="exec")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
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


def prepare(
    destination: Path,
    generation_result_path: Path,
    package_path: Path,
    expected_package_sha256: str,
) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    if sha256_file(package_path) != expected_package_sha256:
        raise ValueError("candidate package does not match the supplied immutable pin")
    generation = json.loads(generation_result_path.read_text(encoding="utf-8"))
    if generation["audit_id"] != "OIA-1-TRACK-A-005b":
        raise ValueError("generation audit changed")
    if generation["status"] != "revision_generation_feasible":
        raise ValueError("revision generation did not produce a feasible static frontier")
    if generation["package"]["sha256"] != expected_package_sha256:
        raise ValueError("generation result and package pin disagree")
    accepted = [
        row
        for row in generation["candidate_records"]
        if row["status"] == "structurally_accepted_not_executed"
    ]
    candidate_ids = [str(row["candidate_id"]) for row in accepted]
    if len(candidate_ids) < 2 or candidate_ids != sorted(candidate_ids):
        raise ValueError("accepted revision frontier order or size changed")
    if any(not candidate_id.startswith("R") for candidate_id in candidate_ids):
        raise ValueError("unexpected revision candidate id")

    destination.mkdir(parents=True)
    candidate_root = destination / "candidates"
    candidate_root.mkdir()
    calibration_root = destination / "calibration"
    calibration_root.mkdir()
    for name, expected in (
        ("p0.txt", EXPECTED_P0_SHA256),
        ("p1_settled.txt", EXPECTED_P1_SHA256),
    ):
        data = (INPUT_ROOT / name).read_bytes()
        if sha256_bytes(data) != expected:
            raise ValueError(f"calibration raster changed: {name}")
        (calibration_root / name).write_bytes(data)

    records: list[dict[str, object]] = []
    with zipfile.ZipFile(package_path) as archive:
        infos = archive.infolist()
        if len(infos) != len({item.filename for item in infos}):
            raise ValueError("candidate package has duplicate paths")
        if any(
            PurePosixPath(item.filename).is_absolute()
            or ".." in PurePosixPath(item.filename).parts
            for item in infos
        ):
            raise ValueError("candidate package contains an unsafe path")
        package_manifest = json.loads(archive.read("CANDIDATE_MANIFEST.json"))
        if package_manifest["audit_id"] != "OIA-1-TRACK-A-005b":
            raise ValueError("package audit changed")
        if [row["candidate_id"] for row in package_manifest["candidates"]] != candidate_ids:
            raise ValueError("package candidate order changed")
        for candidate in package_manifest["candidates"]:
            candidate_id = candidate["candidate_id"]
            source = archive.read(f"candidates/{candidate_id}/candidate.py")
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
            (output_dir / "candidate.py").write_bytes(source)
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
        "audit_id": "OIA-1-TRACK-A-005b",
        "status": (
            "revision_bundles_prepared_behavior_not_run"
            if len(prepared) >= 2
            else "static_admission_blocker"
        ),
        "generation_result_sha256": sha256_file(generation_result_path),
        "candidate_package_sha256": expected_package_sha256,
        "candidate_records": records,
        "accounting": {
            "source_records_opened": len(accepted),
            "hardened_static_pass": len(prepared),
            "hardened_static_rejected": len(records) - len(prepared),
            "candidate_imports": 0,
            "candidate_processes": 0,
            "candidate_behavior_steps": 0,
            "oia_processes": 0,
            "step_2_or_later_payloads_read": 0,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
        },
        "claim_boundary": (
            "Opened revision-source static admission only; no candidate import, "
            "calibration, later behavior, OIA execution, or step-2 access."
        ),
    }
    (destination / "PREPARED_BUNDLES.json").write_bytes(pretty_bytes(result))
    make_read_only(destination)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--generation-result", type=Path, required=True)
    parser.add_argument("--candidate-package", type=Path, required=True)
    parser.add_argument("--expected-package-sha256", required=True)
    args = parser.parse_args()
    result = prepare(
        args.destination.resolve(),
        args.generation_result.resolve(),
        args.candidate_package.resolve(),
        args.expected_package_sha256,
    )
    print(
        json.dumps(
            {
                "prepared": result["accounting"]["hardened_static_pass"],
                "rejected": result["accounting"]["hardened_static_rejected"],
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
