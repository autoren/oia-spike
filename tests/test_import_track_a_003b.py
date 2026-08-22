from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

from scripts.import_track_a_003b import (
    TRACK_A_003B_ATTEMPT_02,
    file_sha256,
    verify_and_extract,
)


def make_package(root: Path, *, unsafe_name: str | None = None) -> tuple[Path, object]:
    selected_data = b"candidate bytes\n"
    selected_hash = hashlib.sha256(selected_data).hexdigest()
    archive_md5 = "1" * 32
    archive_sha256 = "2" * 64
    summary = {
        "attempt_id": "test-attempt",
        "selected_file_count": 1,
        "selected_total_bytes": len(selected_data),
        "candidate_execution": False,
        "arc_execution": False,
        "paid_or_model_api_calls": False,
        "credentials_used": False,
    }
    files = {
        "ACQUISITION_SUMMARY.json": (json.dumps(summary, sort_keys=True) + "\n").encode(),
        "ARCHIVE_MD5SUMS.txt": f"{archive_md5}  source.tar.gz\n".encode(),
        "ARCHIVE_SHA256SUMS.txt": f"{archive_sha256}  source.tar.gz\n".encode(),
        "ARCHIVE_SIZE.txt": b"source.tar.gz 123 bytes\n",
        "SELECTED_FILE_MANIFEST.json": (
            json.dumps(
                [{"path": "run/file.bin", "sha256": selected_hash, "size": len(selected_data)}],
                sort_keys=True,
            )
            + "\n"
        ).encode(),
        "selected/run/file.bin": selected_data,
    }
    checksums = "".join(
        f"{hashlib.sha256(data).hexdigest()}  ./{name}\n" for name, data in sorted(files.items())
    ).encode()
    files["PAYLOAD_SHA256SUMS.txt"] = checksums

    package_name = "test-package.tar.gz"
    package = root / package_name
    with tarfile.open(package, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        if unsafe_name:
            info = tarfile.TarInfo(unsafe_name)
            info.size = 1
            archive.addfile(info, io.BytesIO(b"x"))

    package_hash = file_sha256(package)
    checksum_name = "PACKAGE_SHA256SUMS.txt"
    artifact = root / "artifact.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.write(package, package_name)
        archive.writestr(checksum_name, f"{package_hash}  ../{package_name}\n")

    contract = replace(
        TRACK_A_003B_ATTEMPT_02,
        artifact_id=1,
        zip_size=artifact.stat().st_size,
        zip_sha256=file_sha256(artifact),
        package_name=package_name,
        package_size=package.stat().st_size,
        package_sha256=package_hash,
        checksum_name=checksum_name,
        archive_size=123,
        archive_md5=archive_md5,
        archive_sha256=archive_sha256,
        attempt_id="test-attempt",
        selected_file_count=1,
        selected_total_bytes=len(selected_data),
    )
    return artifact, contract


class ImportTrackA003bTests(unittest.TestCase):
    def test_verified_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact, contract = make_package(root)
            destination = root / "imported"
            report = verify_and_extract(
                artifact, destination, contract=contract, make_read_only=False
            )
            self.assertEqual(report["status"], "verified_read_only_import")
            self.assertTrue(report["integrity"]["payload_manifest_verified"])
            self.assertEqual(
                (destination / "selected/run/file.bin").read_bytes(), b"candidate bytes\n"
            )

    def test_read_only_import_is_installed_before_permissions_are_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact, contract = make_package(root)
            destination = root / "imported"
            try:
                report = verify_and_extract(artifact, destination, contract=contract)
                self.assertTrue(report["integrity"]["materialized_read_only"])
                self.assertEqual(destination.stat().st_mode & 0o222, 0)
                self.assertEqual(
                    (destination / "selected/run/file.bin").stat().st_mode & 0o222, 0
                )
            finally:
                if destination.exists():
                    destination.chmod(0o755)
                    for path in destination.rglob("*"):
                        path.chmod(0o755 if path.is_dir() else 0o644)

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact, contract = make_package(root, unsafe_name="../escape")
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                verify_and_extract(
                    artifact, root / "imported", contract=contract, make_read_only=False
                )
            self.assertFalse((root / "escape").exists())


if __name__ == "__main__":
    unittest.main()
