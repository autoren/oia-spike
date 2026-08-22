#!/usr/bin/env python3
"""Prepare merged Track A 005c normalized sources without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_ROOT = ROOT / "audits" / "track-a-005b" / "revision-input"
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
EXPECTED_P1_SHA256 = "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"

sys.path.insert(0, str(ROOT / "scripts"))
from prepare_track_a_005b_admission import hardened_static_scan, make_read_only


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def prepare(
    destination: Path,
    result_path: Path,
    package_path: Path,
    expected_package_sha256: str,
) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    if sha256_file(package_path) != expected_package_sha256:
        raise ValueError("normalized package pin changed")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (
        result["audit_id"] != "OIA-1-TRACK-A-005c"
        or result["status"] != "maintenance_normalization_feasible"
        or result["package"]["sha256"] != expected_package_sha256
    ):
        raise ValueError("normalization result is not a merged feasible package")
    destination.mkdir(parents=True)
    (destination / "candidates").mkdir()
    calibration = destination / "calibration"
    calibration.mkdir()
    for name, expected in (
        ("p0.txt", EXPECTED_P0_SHA256),
        ("p1_settled.txt", EXPECTED_P1_SHA256),
    ):
        data = (CALIBRATION_ROOT / name).read_bytes()
        if sha256_bytes(data) != expected:
            raise ValueError(f"calibration source changed: {name}")
        (calibration / name).write_bytes(data)

    records = []
    with zipfile.ZipFile(package_path) as archive:
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("normalized package has duplicate paths")
        if any(
            PurePosixPath(info.filename).is_absolute()
            or ".." in PurePosixPath(info.filename).parts
            for info in infos
        ):
            raise ValueError("normalized package has unsafe paths")
        manifest = json.loads(archive.read("CANDIDATE_MANIFEST.json"))
        candidates = manifest["candidates"]
        if len(candidates) != 8 or [row["candidate_id"] for row in candidates] != [
            f"R{index:04d}" for index in range(1, 9)
        ]:
            raise ValueError("normalized candidate order changed")
        for candidate in candidates:
            candidate_id = candidate["candidate_id"]
            source = archive.read(f"candidates/{candidate_id}/candidate.py")
            if sha256_bytes(source) != candidate["normalized_sha256"]:
                raise ValueError(f"normalized source hash changed: {candidate_id}")
            scan = hardened_static_scan(source.decode("utf-8"))
            output = destination / "candidates" / candidate_id
            output.mkdir()
            (output / "candidate.py").write_bytes(source)
            records.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_sha256": candidate["normalized_sha256"],
                    "parent_sha256": candidate["parent_sha256"],
                    "candidate_size_bytes": len(source),
                    "stance_id": candidate["stance_id"],
                    "static_scan": scan,
                    "status": "prepared_not_imported_or_executed",
                }
            )
    prepared = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005c",
        "status": "revision_bundles_prepared_behavior_not_run",
        "normalization_result_sha256": sha256_file(result_path),
        "normalized_candidate_package_sha256": expected_package_sha256,
        "candidate_records": records,
        "accounting": {
            "source_records_opened": 8,
            "hardened_static_pass": 8,
            "hardened_static_rejected": 0,
            "candidate_imports": 0,
            "candidate_processes": 0,
            "oia_processes": 0,
            "step_2_or_later_payloads_read": 0,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
        },
        "claim_boundary": "Static preparation of deterministic maintenance-normalized sources only; no candidate import, execution, OIA, or step-2 access.",
    }
    (destination / "PREPARED_BUNDLES.json").write_bytes(pretty_bytes(prepared))
    make_read_only(destination)
    return prepared


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--normalization-result", type=Path, required=True)
    parser.add_argument("--normalized-package", type=Path, required=True)
    parser.add_argument("--expected-package-sha256", required=True)
    args = parser.parse_args()
    result = prepare(
        args.destination.resolve(),
        args.normalization_result.resolve(),
        args.normalized_package.resolve(),
        args.expected_package_sha256,
    )
    print(json.dumps({"prepared": len(result["candidate_records"]), "status": result["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
