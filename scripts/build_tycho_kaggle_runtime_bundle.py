#!/usr/bin/env python3
"""Build and portability-test the frozen Tycho Kaggle llama.cpp runtime bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid


OCI_IMAGE = (
    "ghcr.io/ggml-org/llama.cpp@"
    "sha256:faebc1dd2e96e4ab9708e786f16477162ef8f3330d4a4838c371220409870fed"
)
OCI_MANIFEST_DIGEST = (
    "sha256:faebc1dd2e96e4ab9708e786f16477162ef8f3330d4a4838c371220409870fed"
)
OCI_CONFIG_DIGEST = (
    "sha256:ab11a04881d546069880d4b0a1c204e7146ae7bdcb9bd0340ab3ae498926bfc6"
)
CLEAN_IMAGE = (
    "ubuntu@sha256:1e0a86e57d247923571b75e0aaf48a1449cf8c543d51fb3e07a4a7d7bfa79316"
)
EXPECTED_VERSION = "version: 10236 (1464c62d8)"
MAXIMUM_BYTES = 5_000_000_000

COPY_FILES = {
    "/usr/local/cuda/lib64/libcudart.so.13.3.29": "cuda/libcudart.so.13.3.29",
    "/usr/local/cuda/lib64/libcublas.so.13.5.1.27": "cuda/libcublas.so.13.5.1.27",
    "/usr/local/cuda/lib64/libcublasLt.so.13.5.1.27": "cuda/libcublasLt.so.13.5.1.27",
    "/usr/lib/x86_64-linux-gnu/libgomp.so.1.0.0": "syslib/libgomp.so.1.0.0",
    "/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33": "syslib/libstdc++.so.6.0.33",
    "/lib/x86_64-linux-gnu/libgcc_s.so.1": "syslib/libgcc_s.so.1",
    "/usr/lib/x86_64-linux-gnu/libssl.so.3": "syslib/libssl.so.3",
    "/usr/lib/x86_64-linux-gnu/libcrypto.so.3": "syslib/libcrypto.so.3",
}
SYMLINKS = {
    "cuda/libcudart.so.13": "libcudart.so.13.3.29",
    "cuda/libcublas.so.13": "libcublas.so.13.5.1.27",
    "cuda/libcublasLt.so.13": "libcublasLt.so.13.5.1.27",
    "syslib/libgomp.so.1": "libgomp.so.1.0.0",
    "syslib/libstdc++.so.6": "libstdc++.so.6.0.33",
}


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_manifest(root: Path) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    total = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append(
                {"path": relative, "kind": "symlink", "target": os.readlink(path)}
            )
        elif path.is_file():
            size = path.stat().st_size
            total += size
            entries.append(
                {
                    "path": relative,
                    "kind": "file",
                    "bytes": size,
                    "sha256": sha256(path),
                    "executable": bool(path.stat().st_mode & 0o111),
                }
            )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema_version": "OIA-TYCHO-KAGGLE-RUNTIME-FILES-0.1",
        "source_oci_manifest_digest": OCI_MANIFEST_DIGEST,
        "source_oci_config_digest": OCI_CONFIG_DIGEST,
        "file_count": sum(entry["kind"] == "file" for entry in entries),
        "symlink_count": sum(entry["kind"] == "symlink" for entry in entries),
        "total_file_bytes": total,
        "entries_sha256": hashlib.sha256(canonical).hexdigest(),
        "entries": entries,
    }


def inspect_image() -> None:
    inspected = run(
        ["docker", "image", "inspect", OCI_IMAGE, "--format", "{{json .Config}}"],
        capture=True,
    )
    config = json.loads(inspected.stdout)
    labels = config.get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != (
        "1464c62d88f699ec9700c8010bbfdbc603a9efd6"
    ):
        raise RuntimeError("OCI source revision does not match the freeze")
    if labels.get("org.opencontainers.image.version") != "b10236":
        raise RuntimeError("OCI release version does not match the freeze")
    if config.get("Entrypoint") != ["/app/llama-server"]:
        raise RuntimeError("OCI entrypoint does not match the freeze")


def portability_test(output: Path) -> dict[str, object]:
    mount = f"{output.resolve()}:/bundle:ro"
    common = [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--read-only",
        "--volume",
        mount,
        "--env",
        "LD_LIBRARY_PATH=/bundle/app:/bundle/cuda:/bundle/syslib",
        CLEAN_IMAGE,
    ]
    version = run([*common, "/bundle/app/llama-server", "--version"], capture=True)
    version_text = (version.stdout + version.stderr).strip()
    if EXPECTED_VERSION not in version_text:
        raise RuntimeError(f"unexpected llama-server version output: {version_text!r}")
    linkage = run(
        [*common, "/bin/sh", "-c", "ldd /bundle/app/libggml-cuda.so"],
        capture=True,
    )
    unresolved = sorted(
        line.strip().split()[0]
        for line in linkage.stdout.splitlines()
        if "not found" in line
    )
    if unresolved != ["libcuda.so.1"]:
        raise RuntimeError(f"unexpected unresolved libraries: {unresolved}")
    required_bundle_libraries = [
        "libcudart.so.13",
        "libcublas.so.13",
        "libcublasLt.so.13",
    ]
    if not all(f"/bundle/cuda/{name}" in linkage.stdout for name in required_bundle_libraries):
        raise RuntimeError("CUDA user-space libraries did not resolve from the bundle")
    return {
        "clean_image": CLEAN_IMAGE,
        "network": "none",
        "root_filesystem": "read_only",
        "bundle_mount": "read_only",
        "version_output": version_text,
        "unresolved_shared_libraries": unresolved,
        "user_space_cuda_libraries_resolved_from_bundle": True,
    }


def build(output: Path) -> dict[str, object]:
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required to acquire the frozen OCI layers locally")
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output must be absent or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    (output / "app").mkdir()
    (output / "cuda").mkdir()
    (output / "syslib").mkdir()

    run(["docker", "pull", "--platform", "linux/amd64", OCI_IMAGE])
    inspect_image()
    container = f"oia-tycho-package-{uuid.uuid4().hex[:16]}"
    run(["docker", "create", "--platform", "linux/amd64", "--name", container, OCI_IMAGE])
    try:
        run(["docker", "cp", f"{container}:/app/.", str(output / "app")])
        for source, destination in COPY_FILES.items():
            run(["docker", "cp", f"{container}:{source}", str(output / destination)])
    finally:
        run(["docker", "rm", "-f", container])
    for relative, target in SYMLINKS.items():
        (output / relative).symlink_to(target)

    manifest = file_manifest(output)
    if int(manifest["total_file_bytes"]) > MAXIMUM_BYTES:
        raise RuntimeError("runtime bundle exceeds the frozen size cap")
    portability = portability_test(output)
    manifest["portability_test"] = portability
    manifest_path = output / "RUNTIME_BUNDLE_FILE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sums = [
        f"{entry['sha256']}  {entry['path']}"
        for entry in manifest["entries"]
        if entry["kind"] == "file"
    ]
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing to build without --execute")
    manifest = build(args.output)
    print(
        json.dumps(
            {
                "entries_sha256": manifest["entries_sha256"],
                "file_count": manifest["file_count"],
                "status": "runtime_bundle_built_and_portability_tested",
                "total_file_bytes": manifest["total_file_bytes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
