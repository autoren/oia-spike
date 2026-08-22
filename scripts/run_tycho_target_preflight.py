#!/usr/bin/env python3
"""Run the model-free Tycho/Sandlock isolation preflight on a target host."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import threading


SANDLOCK_SHA256 = "86f80d68afe0146287ee9b950ca0223945fe49e8722f6c80ffb89eb623e53b27"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def serve(tcp: socket.socket, udp: socket.socket, stop: threading.Event) -> None:
    tcp.settimeout(0.1)
    udp.settimeout(0.1)
    while not stop.is_set():
        try:
            connection, _ = tcp.accept()
            connection.close()
        except TimeoutError:
            pass
        try:
            udp.recvfrom(4096)
        except TimeoutError:
            pass


def blocked(reason: str, detail: str = "") -> None:
    print(
        json.dumps(
            {
                "schema_version": "OIA-TYCHO-TARGET-PREFLIGHT-0.1",
                "verdict": "target_sandlock_preflight_blocked",
                "reason": reason,
                "detail": detail[:4000],
                "host_fallback_used": False,
                "model_loads": 0,
                "gpu_runs": 0,
                "arc_actions": 0,
                "oia_runs": 0,
            },
            sort_keys=True,
        )
    )
    raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--work-root", type=Path, default=Path("/kaggle/working/oia-tycho-preflight"))
    parser.add_argument("--protected-root", type=Path, default=Path("/kaggle/input"))
    args = parser.parse_args()

    bundle = args.bundle_root.resolve(strict=True)
    sandlock = (bundle / "bin" / "sandlock").resolve(strict=True)
    if sha256(sandlock) != SANDLOCK_SHA256:
        blocked("sandlock_hash_mismatch")
    protected = args.protected_root.resolve(strict=True)
    if not protected.is_dir():
        blocked("protected_root_is_not_directory", str(protected))
    work_root = args.work_root.resolve()
    work_root.mkdir(parents=True, exist_ok=False)
    sandlock.chmod(0o755)

    feature = subprocess.run(
        [str(sandlock), "check"], capture_output=True, text=True, check=False, timeout=10
    )
    feature_text = (feature.stdout + feature.stderr).strip()
    if feature.returncode != 0 or "Status:         OK" not in feature.stdout:
        blocked("sandlock_feature_check_failed", feature_text)

    sys.path.insert(0, str(bundle / "runtime"))
    from tycho.workspace import sandbox as sandbox_module
    from tycho.workspace.sandbox import PythonSandbox

    # The exact feature check above is authoritative and captured. Avoid running
    # it a second time during explicit runtime resolution.
    sandbox_module._runtime_usable = lambda name, timeout=8.0: name == "sandlock"
    os.environ["TYCHO_SANDLOCK_BINARY"] = str(sandlock)

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind(("127.0.0.1", 0))
    tcp.listen()
    tcp_port = tcp.getsockname()[1]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp_port = udp.getsockname()[1]
    stop = threading.Event()
    server = threading.Thread(target=serve, args=(tcp, udp, stop), daemon=True)
    server.start()
    with socket.create_connection(("127.0.0.1", tcp_port), timeout=1):
        tcp_control = True
    udp_control = udp.sendto(b"control", ("127.0.0.1", udp_port)) == 7

    source = f'''\
import json
from pathlib import Path
import socket
import subprocess

def attempt(name, fn):
    try:
        value = fn()
        return {{"name": name, "allowed": True, "value": repr(value)[:160]}}
    except BaseException as exc:
        return {{"name": name, "allowed": False, "error_type": type(exc).__name__,
                "errno": getattr(exc, "errno", None), "error": str(exc)[:160]}}

def tcp_connect():
    sock = socket.create_connection(("127.0.0.1", {tcp_port}), timeout=1)
    sock.close()
    return True

def udp_send():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return sock.sendto(b"probe", ("127.0.0.1", {udp_port}))
    finally:
        sock.close()

grid = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
rotated = [list(row) for row in zip(*grid[::-1])]
Path("result.json").write_text(json.dumps({{"rotated": rotated}}, sort_keys=True) + "\\n")
attempts = [
    attempt("workspace_read", lambda: Path("input.json").read_text()),
    attempt("workspace_write", lambda: Path("scratch.txt").write_text("ok\\n")),
    attempt("sibling_sentinel_read", lambda: Path("../sentinel.txt").read_text()),
    attempt("host_etc_passwd_read", lambda: Path("/etc/passwd").read_text()),
    attempt("protected_root_read", lambda: list(Path({str(protected)!r}).iterdir())),
    attempt("outside_write", lambda: Path("../escape.txt").write_text("escaped\\n")),
    attempt("tcp_connect", tcp_connect),
    attempt("udp_send", udp_send),
    attempt("subprocess_spawn", lambda: subprocess.run(
        ["/usr/bin/id"], check=True, capture_output=True, text=True, timeout=2
    ).stdout),
]
print(json.dumps({{"grid_result": rotated, "attempts": attempts}}, sort_keys=True))
'''

    workspace = work_root / "workspace"
    workspace.mkdir()
    (workspace / "input.json").write_text(
        '{"task":"representative_grid_rotation"}\n', encoding="utf-8"
    )
    (work_root / "sentinel.txt").write_text("must-not-be-readable\n", encoding="utf-8")
    sandbox = PythonSandbox(runtime="sandlock")
    try:
        functional = sandbox.run_source(workspace, source, timeout=10)
        timeout_result = sandbox.run_source(workspace, "while True:\n    pass\n", timeout=1)
    finally:
        stop.set()
        server.join(timeout=1)
        tcp.close()
        udp.close()

    memory_script = workspace / "memory_probe.py"
    memory_script.write_text(
        "print('MEMORY_PROBE_STARTED', flush=True)\n"
        "chunks = []\nwhile True:\n    chunks.append(bytearray(8 * 1024 * 1024))\n",
        encoding="utf-8",
    )
    memory_command = [
        str(sandlock), "run",
    ]
    memory_roots = [Path("/usr"), Path("/lib"), Path("/etc/ld.so.cache")]
    memory_roots.extend(Path(value) for value in sorted({sys.prefix, sys.base_prefix}))
    for root in dict.fromkeys(str(path.resolve()) for path in memory_roots if path.exists()):
        memory_command.extend(["--fs-read", root])
    memory_command.extend([
        "--fs-write", str(workspace), "--net-deny", "*",
        "--max-processes", "1", "--max-open-files", "128",
        "--max-memory", "64M", "--timeout", "10", "--clean-env",
        "--env", "PATH=/usr/bin:/bin", "--env", f"HOME={workspace}",
        "--cwd", str(workspace), "--", sys.executable, "-B", str(memory_script),
    ])
    memory = subprocess.run(memory_command, capture_output=True, text=True, check=False, timeout=15)

    if functional.returncode != 0 or functional.timed_out:
        blocked("functional_probe_failed", functional.stderr or functional.stdout)
    payload = json.loads(functional.stdout)
    attempts = {item["name"]: item for item in payload["attempts"]}
    allowed = {"workspace_read", "workspace_write"}
    denied = {
        "sibling_sentinel_read", "host_etc_passwd_read", "protected_root_read",
        "outside_write", "tcp_connect", "udp_send", "subprocess_spawn",
    }
    if any(not attempts[name]["allowed"] for name in allowed):
        blocked("required_workspace_capability_denied")
    if any(attempts[name]["allowed"] for name in denied):
        blocked("forbidden_capability_allowed")
    if (work_root / "escape.txt").exists():
        blocked("outside_write_materialized")
    if not timeout_result.timed_out or timeout_result.returncode != -1:
        blocked("timeout_mapping_failed")
    if memory.returncode == 0 or "MEMORY_PROBE_STARTED" not in memory.stdout:
        blocked("memory_limit_failed")

    print(
        json.dumps(
            {
                "schema_version": "OIA-TYCHO-TARGET-PREFLIGHT-0.1",
                "verdict": "target_sandlock_preflight_pass",
                "platform": platform.platform(),
                "python": sys.version.split()[0],
                "feature_check": feature_text,
                "sandlock_binary_sha256": sha256(sandlock),
                "protected_root": str(protected),
                "unsandboxed_control": {"tcp": tcp_control, "udp": udp_control},
                "grid_result": payload["grid_result"],
                "attempts": payload["attempts"],
                "timeout": {"timed_out": True, "returncode": -1},
                "memory": {"limit": "64M", "returncode": memory.returncode},
                "host_fallback_used": False,
                "model_loads": 0,
                "gpu_runs": 0,
                "arc_actions": 0,
                "oia_runs": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
