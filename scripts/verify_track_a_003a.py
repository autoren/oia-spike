#!/usr/bin/env python3
"""Verify the frozen Track A 003a package without external dependencies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-003a"
MANIFEST_PATH = AUDIT_ROOT / "PACKAGE_MANIFEST.json"
CHECKSUM_PATH = AUDIT_ROOT / "OIA-1-Track-A-003a-SHA256SUMS.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_file(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe manifest path: {relative!r}")
    path = AUDIT_ROOT.joinpath(*pure.parts)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"manifest entry is not a regular file: {relative!r}")
    return path


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported package manifest schema")
    if manifest.get("audit_id") != "OIA-1-TRACK-A-003a":
        raise ValueError("unexpected audit id")

    manifest_hashes: dict[str, str] = {}
    for entry in manifest.get("files", []):
        relative = entry["path"]
        path = safe_file(relative)
        observed_size = path.stat().st_size
        observed_hash = sha256(path)
        if observed_size != entry["size_bytes"]:
            raise ValueError(f"size mismatch: {relative}")
        if observed_hash != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
        manifest_hashes[relative] = observed_hash

    checksum_hashes: dict[str, str] = {}
    for line in CHECKSUM_PATH.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        path = safe_file(relative)
        observed = sha256(path)
        if observed != expected:
            raise ValueError(f"checksum-list mismatch: {relative}")
        checksum_hashes[relative] = expected

    expected_checksum_paths = set(manifest_hashes) - {CHECKSUM_PATH.name}
    if set(checksum_hashes) != expected_checksum_paths:
        raise ValueError("checksum list and package manifest cover different files")

    print(
        json.dumps(
            {
                "audit_id": manifest["audit_id"],
                "manifest_entries": len(manifest_hashes),
                "checksum_entries": len(checksum_hashes),
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
