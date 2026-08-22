#!/usr/bin/env python3
"""Independently verify a Tycho target-preflight directory or deterministic ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile


FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
MANIFEST_NAME = "BUNDLE_MANIFEST.json"
SUMS_NAME = "SHA256SUMS"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name != path.as_posix():
        raise ValueError(f"unsafe bundle path: {name}")
    return name


def verify_directory(root: Path) -> dict:
    root = root.resolve(strict=True)
    manifest_path = root / MANIFEST_NAME
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload["schema_version"] != "OIA-TYCHO-TARGET-PREFLIGHT-BUNDLE-0.1":
        raise ValueError("bundle schema changed")
    entries = payload["entries"]
    expected_paths = [safe_name(entry["path"]) for entry in entries]
    if expected_paths != sorted(expected_paths) or len(set(expected_paths)) != len(expected_paths):
        raise ValueError("manifest entries are not unique and sorted")
    actual_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {MANIFEST_NAME, SUMS_NAME}
    )
    if actual_paths != expected_paths:
        raise ValueError("bundle file inventory changed")
    for entry in entries:
        path = root / entry["path"]
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"bundle file changed: {entry['path']}")
        observed_mode = stat.S_IMODE(path.stat().st_mode)
        if observed_mode != entry["mode"]:
            raise ValueError(f"bundle mode changed: {entry['path']}")
    sums = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
    if (root / SUMS_NAME).read_text(encoding="utf-8") != sums:
        raise ValueError("SHA256SUMS changed")
    binary = root / "bin" / "sandlock"
    header = binary.read_bytes()[:20]
    if header[:4] != b"\x7fELF" or header[4] != 2 or header[5] != 1:
        raise ValueError("Sandlock is not little-endian ELF64")
    machine = int.from_bytes(header[18:20], "little")
    if machine != 62:
        raise ValueError("Sandlock ELF machine is not x86-64")
    runner = (root / "run_target_preflight.py").read_text(encoding="utf-8")
    required = {
        '"Status:         OK"',
        '"protected_root_read"',
        '"--net-deny", "*"',
        '"--max-processes", "1"',
        '"MEMORY_PROBE_STARTED"',
        '"host_fallback_used": False',
        '"model_loads": 0',
        '"arc_actions": 0',
        '"oia_runs": 0',
    }
    if any(token not in runner for token in required):
        raise ValueError("target runner contract changed")
    forbidden = {"TYCHO_SANDBOX_RUNTIME=host", 'runtime="host"', "kagglehub", "requests."}
    if any(token in runner for token in forbidden):
        raise ValueError("target runner includes a forbidden fallback or service")
    return {
        "entry_count": len(entries),
        "entries_sha256": payload["entries_sha256"],
        "sandlock_elf_machine": "x86-64",
        "total_file_bytes": sum(entry["bytes"] for entry in entries),
    }


def verify_zip(path: Path) -> dict:
    path = path.resolve(strict=True)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [safe_name(info.filename) for info in infos]
        if names != sorted(names) or len(set(names)) != len(names):
            raise ValueError("ZIP paths are not unique and sorted")
        if any(info.date_time != FIXED_ZIP_TIME for info in infos):
            raise ValueError("ZIP timestamps are not fixed")
        with tempfile.TemporaryDirectory(prefix="oia-target-preflight-verify-") as temporary:
            root = Path(temporary)
            for info in infos:
                destination = root / info.filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(info))
                destination.chmod((info.external_attr >> 16) & 0o777)
            result = verify_directory(root)
    result.update({"zip_bytes": path.stat().st_size, "zip_sha256": sha256(path)})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    result = verify_directory(args.bundle) if args.bundle.is_dir() else verify_zip(args.bundle)
    print(json.dumps({"status": "offline_target_preflight_bundle_verified", **result}, sort_keys=True))


if __name__ == "__main__":
    main()
