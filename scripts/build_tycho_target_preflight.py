#!/usr/bin/env python3
"""Build the frozen deterministic offline Tycho target-preflight bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "integrations/tycho-target-preflight/PREFLIGHT_PACKAGE_PROTOCOL.json"
PATCH = ROOT / "integrations/tycho-sandlock/sandlock-python-sandbox-v0.1.patch"
RUNNER = ROOT / "scripts/run_tycho_target_preflight.py"
VERIFIER = ROOT / "scripts/verify_offline_tycho_target_preflight.py"
TARGET_README = ROOT / "integrations/tycho-target-preflight/TARGET_README.md"
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> None:
    if sha256(path) != expected:
        raise RuntimeError(f"{label} hash does not match the freeze")


def extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            name = Path(member.name)
            if name.is_absolute() or ".." in name.parts or member.issym() or member.islnk():
                raise RuntimeError(f"unsafe archive member: {member.name}")
        handle.extractall(destination, filter="data")


def normalize_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            executable = path == root / "bin/sandlock" or path.suffix == ".py"
            path.chmod(0o755 if executable else 0o644)


def manifest(root: Path, protocol: dict) -> dict:
    entries = []
    for path in sorted(value for value in root.rglob("*") if value.is_file()):
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "mode": path.stat().st_mode & 0o777,
            }
        )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": "OIA-TYCHO-TARGET-PREFLIGHT-BUNDLE-0.1",
        "gate_id": protocol["gate_id"],
        "source_oia_spike_commit": protocol["parent_evidence"]["oia_spike_merge_commit"],
        "sandlock_asset_sha256": protocol["frozen_inputs"]["sandlock_release_asset"]["sha256"],
        "sandlock_binary_sha256": protocol["frozen_inputs"]["sandlock_release_asset"]["binary_sha256"],
        "tycho_commit": protocol["frozen_inputs"]["tycho_source"]["commit"],
        "tycho_archive_sha256": protocol["frozen_inputs"]["tycho_source"]["archive_sha256"],
        "tycho_patch_sha256": protocol["frozen_inputs"]["tycho_patch"]["sha256"],
        "entries_sha256": hashlib.sha256(canonical).hexdigest(),
        "entries": entries,
    }


def write_zip(root: Path, output: Path) -> None:
    files = sorted(value for value in root.rglob("*") if value.is_file())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0o777) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(args: argparse.Namespace) -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    frozen = protocol["frozen_inputs"]
    verify(args.sandlock_asset, frozen["sandlock_release_asset"]["sha256"], "Sandlock asset")
    verify(args.sandlock_license, frozen["sandlock_license"]["sha256"], "Sandlock license")
    verify(args.tycho_archive, frozen["tycho_source"]["archive_sha256"], "Tycho archive")
    verify(PATCH, frozen["tycho_patch"]["sha256"], "Tycho patch")
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError("output directory must be absent or empty")
    args.output.mkdir(parents=True, exist_ok=True)
    bundle = args.output / "bundle"
    bundle.mkdir()
    with tempfile.TemporaryDirectory(prefix="oia-target-preflight-build-") as temporary:
        scratch = Path(temporary)
        sandlock_root = scratch / "sandlock"
        tycho_root = scratch / "tycho"
        sandlock_root.mkdir()
        tycho_root.mkdir()
        extract(args.sandlock_asset, sandlock_root)
        extract(args.tycho_archive, tycho_root)
        sandlock_binary = next(path for path in sandlock_root.rglob("sandlock") if path.is_file())
        verify(sandlock_binary, frozen["sandlock_release_asset"]["binary_sha256"], "Sandlock binary")
        source = next(path for path in tycho_root.iterdir() if path.is_dir())
        subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=source, check=True)
        subprocess.run(["git", "apply", str(PATCH)], cwd=source, check=True)
        (bundle / "bin").mkdir()
        shutil.copy2(sandlock_binary, bundle / "bin/sandlock")
        (bundle / "runtime").mkdir()
        shutil.copytree(source / "tycho", bundle / "runtime/tycho")
        (bundle / "source").mkdir()
        shutil.copy2(args.sandlock_asset, bundle / "source/sandlock-x86_64-v0.8.6.tar.gz")
        shutil.copy2(args.tycho_archive, bundle / "source/tycho-f68912a.tar.gz")
        shutil.copy2(PATCH, bundle / "source/sandlock-python-sandbox-v0.1.patch")
        (bundle / "licenses").mkdir()
        shutil.copy2(args.sandlock_license, bundle / "licenses/SANDLOCK_LICENSE")
        shutil.copy2(source / "LICENSE", bundle / "licenses/TYCHO_LICENSE")
    shutil.copy2(RUNNER, bundle / "run_target_preflight.py")
    shutil.copy2(VERIFIER, bundle / "verify_offline_bundle.py")
    shutil.copy2(TARGET_README, bundle / "README.md")
    normalize_tree(bundle)
    payload = manifest(bundle, protocol)
    (bundle / "BUNDLE_MANIFEST.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sums = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in payload["entries"])
    (bundle / "SHA256SUMS").write_text(sums, encoding="utf-8")
    (bundle / "BUNDLE_MANIFEST.json").chmod(0o644)
    (bundle / "SHA256SUMS").chmod(0o644)
    zip_path = args.output / "tycho-target-preflight-r2a.zip"
    write_zip(bundle, zip_path)
    maximum = protocol["bundle_contract"]["maximum_bytes"]
    if zip_path.stat().st_size > maximum:
        raise RuntimeError("offline preflight ZIP exceeds the frozen size cap")
    result = {
        "schema_version": "OIA-TYCHO-TARGET-PREFLIGHT-BUILD-0.1",
        "status": "offline_target_preflight_bundle_built",
        "entry_count": len(payload["entries"]),
        "entries_sha256": payload["entries_sha256"],
        "total_file_bytes": sum(entry["bytes"] for entry in payload["entries"]),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256(zip_path),
    }
    (args.output / "BUILD_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--sandlock-asset", type=Path, required=True)
    parser.add_argument("--sandlock-license", type=Path, required=True)
    parser.add_argument("--tycho-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing to build without --execute")
    print(json.dumps(build(args), sort_keys=True))


if __name__ == "__main__":
    main()
