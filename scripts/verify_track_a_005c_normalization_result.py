#!/usr/bin/env python3
"""Verify Track A 005c normalized package without executing candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005c"
RESULT_ROOT = AUDIT_ROOT / "normalization-result"
RESULT_PATH = RESULT_ROOT / "NORMALIZATION_RESULT.json"
PACKAGE_PATH = RESULT_ROOT / "NORMALIZED_CANDIDATE_PACKAGE.zip"
PARENT_PACKAGE = ROOT / "audits" / "track-a-005b" / "revision-generation" / "CANDIDATE_PACKAGE.zip"
EXPECTED_PARENT_PACKAGE_SHA256 = "a49a8012b0f7f130feb5c32bfb32825ad4426d7c2203fba6e532165c1fd884d4"

sys.path.insert(0, str(ROOT / "scripts"))
from normalize_track_a_005c_candidates import normalize_source


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> None:
    if not RESULT_PATH.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005c", "status": "prenormalization"}))
        return
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    if result["status"] not in {
        "maintenance_normalization_feasible",
        "maintenance_normalization_blocker",
    }:
        raise ValueError("unexpected 005c normalization verdict")
    if sha256(PARENT_PACKAGE) != EXPECTED_PARENT_PACKAGE_SHA256:
        raise ValueError("005c parent package changed")
    package = result["package"]
    if PACKAGE_PATH.stat().st_size != package["size_bytes"] or sha256(PACKAGE_PATH) != package["sha256"]:
        raise ValueError("005c normalized package identity changed")
    records = result["candidate_records"]
    if [row["candidate_id"] for row in records] != [f"R{index:04d}" for index in range(1, 9)]:
        raise ValueError("005c candidate order changed")

    with zipfile.ZipFile(PARENT_PACKAGE) as parent, zipfile.ZipFile(PACKAGE_PATH) as normalized:
        infos = normalized.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("005c normalized package duplicate paths")
        if [info.filename for info in infos] != sorted(info.filename for info in infos):
            raise ValueError("005c normalized package order changed")
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise ValueError(f"unsafe 005c normalized path: {info.filename}")
            if info.date_time != (1980, 1, 1, 0, 0, 0) or (info.external_attr >> 16) != 0o100444:
                raise ValueError(f"005c deterministic ZIP metadata changed: {info.filename}")
        manifest_bytes = normalized.read("CANDIDATE_MANIFEST.json")
        if sha256_bytes(manifest_bytes) != package["manifest_sha256"]:
            raise ValueError("005c package manifest hash changed")
        manifest = json.loads(manifest_bytes)
        expected_names = {"CANDIDATE_MANIFEST.json"}
        normalized_records = {
            row["candidate_id"]: row
            for row in records
            if row["status"] == "normalized_not_executed"
        }
        for candidate in manifest["candidates"]:
            candidate_id = candidate["candidate_id"]
            parent_source = parent.read(f"candidates/{candidate_id}/candidate.py")
            expected_source, expected_edit = normalize_source(parent_source)
            source_name = f"candidates/{candidate_id}/candidate.py"
            source = normalized.read(source_name)
            record = normalized_records[candidate_id]
            if source != expected_source:
                raise ValueError(f"005c transformation changed: {candidate_id}")
            if record["normalization"] != expected_edit:
                raise ValueError(f"005c edit record changed: {candidate_id}")
            if sha256_bytes(parent_source) != record["parent_sha256"]:
                raise ValueError(f"005c parent hash changed: {candidate_id}")
            if sha256_bytes(source) != record["normalized_sha256"]:
                raise ValueError(f"005c normalized hash changed: {candidate_id}")
            expected_names.add(source_name)
        if {info.filename for info in infos} != expected_names:
            raise ValueError("005c normalized package entry set changed")
    accepted = [row for row in records if row["status"] == "normalized_not_executed"]
    accounting = result["accounting"]
    if accounting["normalized_candidates"] != len(accepted):
        raise ValueError("005c normalized accounting changed")
    if result["status"] == "maintenance_normalization_feasible" and len(accepted) != 8:
        raise ValueError("005c feasible result is incomplete")
    if result["status"] == "maintenance_normalization_blocker" and len(accepted) == 8:
        raise ValueError("005c blocker has complete normalization")
    for field in (
        "model_or_repair_inferences",
        "candidate_imports",
        "candidate_processes",
        "oia_processes",
        "step_2_or_later_payloads_read",
        "real_arc_actions",
        "network_or_service_calls",
    ):
        if accounting[field] != 0:
            raise ValueError(f"005c normalization boundary crossed: {field}")
    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005c",
                "normalized": len(accepted),
                "package_sha256": package["sha256"],
                "pass": True,
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
