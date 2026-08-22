#!/usr/bin/env python3
"""Verify and safely materialize the pinned Track A 003b Actions artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


MIB = 1024 * 1024
MAX_PACKAGE_BYTES = 128 * MIB
MAX_PACKAGE_FILES = 20_000


@dataclass(frozen=True)
class ArtifactContract:
    artifact_id: int
    zip_size: int
    zip_sha256: str
    package_name: str
    package_size: int
    package_sha256: str
    checksum_name: str
    archive_size: int
    archive_md5: str
    archive_sha256: str
    attempt_id: str
    selected_file_count: int
    selected_total_bytes: int


TRACK_A_003B_ATTEMPT_02 = ArtifactContract(
    artifact_id=9465881649,
    zip_size=8_535_286,
    zip_sha256="1b239318741872a339e4a1a31aa3f6876ee298fdb17db328075a343d56a52a1a",
    package_name="track-a-003b-attempt-02-selected-ls20.tar.gz",
    package_size=8_534_786,
    package_sha256="de141756be11b7d54730584ce16d3d0979a9bbd8aef707a73d50ab8a112c2cbf",
    checksum_name="TRACK_A_003B_ATTEMPT_02_PACKAGE_SHA256SUMS.txt",
    archive_size=797_835_543,
    archive_md5="4dd279f099609392c30cffa468801316",
    archive_sha256="c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93",
    attempt_id="003b-02",
    selected_file_count=10_683,
    selected_total_bytes=28_897_676,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(MIB), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_parts(name: str) -> tuple[str, ...]:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe archive path: {name!r}")
    parts = tuple(part for part in pure.parts if part not in ("", "."))
    if not parts and name not in (".", "./"):
        raise ValueError(f"empty archive path: {name!r}")
    return parts


def parse_single_checksum(data: bytes, expected_name: str) -> str:
    text = data.decode("utf-8")
    lines = text.splitlines()
    if len(lines) != 1:
        raise ValueError("inner package checksum file must contain exactly one line")
    digest, relative = lines[0].split(maxsplit=1)
    if Path(relative.lstrip("*")).name != expected_name:
        raise ValueError("inner package checksum names an unexpected file")
    if len(digest) != 64:
        raise ValueError("inner package checksum is not SHA-256")
    return digest


def parse_checksum_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        parts = safe_parts(relative.lstrip("*"))
        normalized = PurePosixPath(*parts).as_posix()
        if normalized in result:
            raise ValueError(f"duplicate checksum entry: {normalized}")
        result[normalized] = digest
    return result


def verify_text_evidence(payload: Path, contract: ArtifactContract) -> None:
    expected = {
        "ARCHIVE_MD5SUMS.txt": contract.archive_md5,
        "ARCHIVE_SHA256SUMS.txt": contract.archive_sha256,
    }
    for name, digest in expected.items():
        line = (payload / name).read_text(encoding="utf-8").strip()
        observed, _ = line.split(maxsplit=1)
        if observed != digest:
            raise ValueError(f"unexpected value in {name}")

    size_line = (payload / "ARCHIVE_SIZE.txt").read_text(encoding="utf-8").strip()
    if size_line.split()[-2:] != [str(contract.archive_size), "bytes"]:
        raise ValueError("unexpected source archive size evidence")


def verify_payload(payload: Path, contract: ArtifactContract) -> dict[str, object]:
    checksum_path = payload / "PAYLOAD_SHA256SUMS.txt"
    checksums = parse_checksum_manifest(checksum_path)
    actual_files = {
        path.relative_to(payload).as_posix()
        for path in payload.rglob("*")
        if path.is_file()
    }
    expected_files = actual_files - {checksum_path.relative_to(payload).as_posix()}
    if set(checksums) != expected_files:
        missing = sorted(expected_files - set(checksums))
        extra = sorted(set(checksums) - expected_files)
        raise ValueError(f"payload checksum coverage mismatch; missing={missing}, extra={extra}")
    for relative, expected in checksums.items():
        if file_sha256(payload / relative) != expected:
            raise ValueError(f"payload checksum mismatch: {relative}")

    summary = json.loads((payload / "ACQUISITION_SUMMARY.json").read_text(encoding="utf-8"))
    expected_summary = {
        "attempt_id": contract.attempt_id,
        "selected_file_count": contract.selected_file_count,
        "selected_total_bytes": contract.selected_total_bytes,
        "candidate_execution": False,
        "arc_execution": False,
        "paid_or_model_api_calls": False,
        "credentials_used": False,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise ValueError(f"unexpected acquisition summary field {key!r}")

    selected_manifest = json.loads(
        (payload / "SELECTED_FILE_MANIFEST.json").read_text(encoding="utf-8")
    )
    if len(selected_manifest) != contract.selected_file_count:
        raise ValueError("selected-file manifest count mismatch")
    selected_files = {
        path.relative_to(payload / "selected").as_posix(): path
        for path in (payload / "selected").rglob("*")
        if path.is_file()
    }
    if len(selected_files) != contract.selected_file_count:
        raise ValueError("materialized selected-file count mismatch")

    selected_total = 0
    seen: set[str] = set()
    for entry in selected_manifest:
        relative = PurePosixPath(*safe_parts(entry["path"])).as_posix()
        if relative in seen or relative not in selected_files:
            raise ValueError(f"invalid selected-file manifest entry: {relative}")
        seen.add(relative)
        path = selected_files[relative]
        if path.stat().st_size != entry["size"]:
            raise ValueError(f"selected-file size mismatch: {relative}")
        if checksums[f"selected/{relative}"] != entry["sha256"]:
            raise ValueError(f"selected-file manifest hash disagreement: {relative}")
        selected_total += entry["size"]
    if seen != set(selected_files) or selected_total != contract.selected_total_bytes:
        raise ValueError("selected-file manifest coverage mismatch")

    verify_text_evidence(payload, contract)
    return summary


def make_tree_read_only(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    directories = [path for path in root.rglob("*") if path.is_dir()]
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        path.chmod(0o555)
    root.chmod(0o555)


def verify_and_extract(
    artifact_zip: Path,
    destination: Path,
    *,
    contract: ArtifactContract = TRACK_A_003B_ATTEMPT_02,
    make_read_only: bool = True,
) -> dict[str, object]:
    artifact_zip = artifact_zip.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise ValueError(f"destination already exists: {destination}")
    if artifact_zip.stat().st_size != contract.zip_size:
        raise ValueError("Actions artifact ZIP size mismatch")
    if file_sha256(artifact_zip) != contract.zip_sha256:
        raise ValueError("Actions artifact ZIP SHA-256 mismatch")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=destination.parent, prefix=f".{destination.name}.partial-"
    ) as temporary:
        temporary_root = Path(temporary)
        package_path = temporary_root / contract.package_name
        payload = temporary_root / "payload"
        payload.mkdir()

        with zipfile.ZipFile(artifact_zip) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            expected_names = {contract.package_name, contract.checksum_name}
            if names != expected_names or len(infos) != len(expected_names):
                raise ValueError("Actions artifact ZIP contains unexpected entries")
            if any(info.is_dir() or info.flag_bits & 1 for info in infos):
                raise ValueError("Actions artifact ZIP contains a directory or encrypted entry")
            checksum_data = archive.read(contract.checksum_name)
            if parse_single_checksum(checksum_data, contract.package_name) != contract.package_sha256:
                raise ValueError("inner checksum file disagrees with the frozen package hash")
            with archive.open(contract.package_name) as source, package_path.open("xb") as target:
                shutil.copyfileobj(source, target, length=MIB)

        if package_path.stat().st_size != contract.package_size:
            raise ValueError("inner package size mismatch")
        if file_sha256(package_path) != contract.package_sha256:
            raise ValueError("inner package SHA-256 mismatch")

        with tarfile.open(package_path, mode="r:gz") as archive:
            members = archive.getmembers()
            files = [member for member in members if member.isfile()]
            directories = [member for member in members if member.isdir()]
            if len(files) > MAX_PACKAGE_FILES:
                raise ValueError("inner package exceeds the file-count limit")
            if sum(member.size for member in files) > MAX_PACKAGE_BYTES:
                raise ValueError("inner package exceeds the uncompressed-size limit")
            if len(files) + len(directories) != len(members):
                raise ValueError("inner package contains links or special filesystem entries")

            normalized: set[tuple[str, ...]] = set()
            for member in members:
                parts = safe_parts(member.name)
                if parts in normalized:
                    raise ValueError(f"duplicate inner package path: {member.name!r}")
                normalized.add(parts)

            for member in members:
                parts = safe_parts(member.name)
                if not parts:
                    continue
                target = payload.joinpath(*parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=False)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot read inner package member: {member.name!r}")
                with source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=MIB)
                if target.stat().st_size != member.size:
                    raise ValueError(f"short extraction: {member.name!r}")

        summary = verify_payload(payload, contract)
        package_path.unlink()
        os.replace(payload, destination)
        if make_read_only:
            make_tree_read_only(destination)

    report = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "status": "verified_read_only_import",
        "source": {
            "repository": "autoren/ontology-intervention-auditor",
            "workflow_run_id": 32537337394,
            "job_id": 96940609408,
            "head_commit": "f5a88d41fb6c4abf34bbd5210ceedd4584ac3416",
        },
        "artifact": {
            "artifact_id": contract.artifact_id,
            "zip_size": contract.zip_size,
            "zip_sha256": contract.zip_sha256,
            "package_name": contract.package_name,
            "package_size": contract.package_size,
            "package_sha256": contract.package_sha256,
        },
        "source_archive": {
            "size": contract.archive_size,
            "md5": contract.archive_md5,
            "sha256": contract.archive_sha256,
        },
        "payload": {
            "tar_members": len(members),
            "tar_files": len(files),
            "tar_directories": len(directories),
            "tar_file_bytes": sum(member.size for member in files),
            "selected_file_count": summary["selected_file_count"],
            "selected_total_bytes": summary["selected_total_bytes"],
            "payload_checksum_entries": len(parse_checksum_manifest(destination / "PAYLOAD_SHA256SUMS.txt")),
        },
        "integrity": {
            "outer_zip_verified": True,
            "inner_package_verified": True,
            "payload_manifest_verified": True,
            "selected_file_manifest_verified": True,
            "safe_regular_files_only": True,
            "materialized_read_only": make_read_only,
        },
        "execution_boundary": {
            "candidate_execution": False,
            "arc_execution": False,
            "paid_or_model_api_calls": False,
            "credentials_used": False,
            "oia_separability": False,
            "track_b_claim": False,
        },
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_zip", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = verify_and_extract(args.artifact_zip, args.destination)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
