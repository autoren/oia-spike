#!/usr/bin/env python3
"""Run the frozen live adapter probe against a patched Tycho checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import sys
import tempfile
import threading


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def listener(tcp: socket.socket, udp: socket.socket, stop: threading.Event) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandlock", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    binary = args.sandlock.resolve(strict=True)
    expected = os.environ.get("OIA_EXPECTED_SANDLOCK_SHA256")
    observed_hash = sha256(binary)
    if expected and observed_hash != expected:
        raise SystemExit("Sandlock binary hash does not match the qualification freeze")
    os.environ["TYCHO_SANDLOCK_BINARY"] = str(binary)

    from tycho.workspace.sandbox import PythonSandbox

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind(("127.0.0.1", 0))
    tcp.listen()
    tcp_port = tcp.getsockname()[1]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp_port = udp.getsockname()[1]
    stop = threading.Event()
    server = threading.Thread(target=listener, args=(tcp, udp, stop), daemon=True)
    server.start()

    with socket.create_connection(("127.0.0.1", tcp_port), timeout=1):
        tcp_control = True
    udp_control = udp.sendto(b"control", ("127.0.0.1", udp_port)) == len(b"control")

    source = f'''\
import json
import os
from pathlib import Path
import socket
import subprocess

def attempt(name, fn):
    try:
        value = fn()
        return {{"name": name, "allowed": True, "value": repr(value)[:160]}}
    except BaseException as exc:
        return {{
            "name": name,
            "allowed": False,
            "error_type": type(exc).__name__,
            "errno": getattr(exc, "errno", None),
            "error": str(exc)[:160],
        }}

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
    attempt("host_users_read", lambda: list(Path("/Users").iterdir())),
    attempt("outside_write", lambda: Path("../escape.txt").write_text("escaped\\n")),
    attempt("tcp_connect", tcp_connect),
    attempt("udp_send", udp_send),
    attempt("subprocess_spawn", lambda: subprocess.run(
        ["/usr/bin/id"], check=True, capture_output=True, text=True, timeout=2
    ).stdout),
]
print(json.dumps({{"grid_result": rotated, "attempts": attempts}}, sort_keys=True))
'''

    try:
        with tempfile.TemporaryDirectory(prefix="oia-sandlock-qualification-") as root:
            base = Path(root)
            workspace = base / "workspace"
            workspace.mkdir()
            (workspace / "input.json").write_text(
                '{"task":"representative_grid_rotation"}\n', encoding="utf-8"
            )
            (base / "sentinel.txt").write_text("must-not-be-readable\n", encoding="utf-8")
            sandbox = PythonSandbox(runtime="sandlock")
            functional = sandbox.run_source(workspace, source, timeout=10)
            timeout_result = sandbox.run_source(workspace, "while True:\n    pass\n", timeout=1)
            escaped = (base / "escape.txt").exists()
    finally:
        stop.set()
        server.join(timeout=1)
        tcp.close()
        udp.close()

    if functional.returncode != 0 or functional.timed_out:
        raise SystemExit(f"functional sandbox probe failed: {functional.stderr!r}")
    payload = json.loads(functional.stdout)
    attempts = {item["name"]: item for item in payload["attempts"]}
    required_allowed = {"workspace_read", "workspace_write"}
    required_denied = {
        "sibling_sentinel_read",
        "host_etc_passwd_read",
        "host_users_read",
        "outside_write",
        "tcp_connect",
        "udp_send",
        "subprocess_spawn",
    }
    if any(not attempts[name]["allowed"] for name in required_allowed):
        raise SystemExit("sandbox denied a required workspace capability")
    if any(attempts[name]["allowed"] for name in required_denied):
        raise SystemExit("sandbox allowed a forbidden capability")
    if payload["grid_result"] != [[6, 3, 0], [7, 4, 1], [8, 5, 2]]:
        raise SystemExit("representative grid transformation changed")
    if escaped:
        raise SystemExit("sandbox wrote outside its workspace")
    if not timeout_result.timed_out or timeout_result.returncode != -1:
        raise SystemExit("Tycho adapter did not map Sandlock timeout to SandboxResult")

    result = {
        "schema_version": "OIA-TYCHO-SANDLOCK-LIVE-PROBE-0.1",
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "sandlock_binary_sha256": observed_hash,
        "runtime_resolution": sandbox.runtime,
        "unsandboxed_control": {"tcp": tcp_control, "udp": udp_control},
        "functional_returncode": functional.returncode,
        "functional_timed_out": functional.timed_out,
        "grid_result": payload["grid_result"],
        "attempts": payload["attempts"],
        "timeout_probe": {
            "returncode": timeout_result.returncode,
            "timed_out": timeout_result.timed_out,
            "stderr": timeout_result.stderr.strip(),
        },
    }
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))


if __name__ == "__main__":
    main()
