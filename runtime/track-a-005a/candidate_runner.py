#!/usr/bin/env python3
"""Candidate-independent isolated runner for one Track A 005a action word."""

from __future__ import annotations

import argparse
import contextlib
import copy  # Preload the only permitted standard-library candidate imports.
import hashlib
import io
import json
import math  # noqa: F401 - preloaded for candidate isolation.
import os
from pathlib import Path
import sys
import types
import typing  # noqa: F401 - preloaded for candidate isolation.

import numpy as np


CANDIDATE_FILE = Path("/candidate/candidate.py")
P0_FILE = Path("/p0/initial_frame.txt")
VALID_ACTIONS = ("ACTION6", "ACTION7")
TERMINAL_SYMBOLS = ("LEVEL_COMPLETED", "GAME_OVER")
FORBIDDEN_AUDIT_PREFIXES = (
    "ctypes.",
    "multiprocessing.",
    "socket.",
    "subprocess.",
)
FORBIDDEN_AUDIT_EVENTS = {
    "os.exec",
    "os.fork",
    "os.forkpty",
    "os.posix_spawn",
    "os.spawn",
    "os.system",
    "pty.spawn",
}


class ForbiddenRuntimeEvent(PermissionError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_ascii_frame(path: Path) -> np.ndarray:
    rows = [
        [int(character, 16) for character in line.strip()]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 64 or any(len(row) != 64 for row in rows):
        raise ValueError("P0 must be a 64x64 hexadecimal raster")
    return np.asarray(rows, dtype=np.int16)


def encode_frame(frame: object) -> bytes:
    array = np.asarray(frame)
    if array.shape != (64, 64):
        raise ValueError("renderer must return a 64x64 raster")
    rows: list[str] = []
    for row in array.tolist():
        if any(not isinstance(value, int) or value < 0 or value > 15 for value in row):
            raise ValueError("renderer returned a non-integer or out-of-range value")
        rows.append("".join(format(value, "X") for value in row))
    return ("\n".join(rows) + "\n").encode("ascii")


def relative_access(path: object) -> str | None:
    if not isinstance(path, (str, bytes, os.PathLike)):
        return None
    try:
        resolved = Path(os.fsdecode(path)).resolve()
    except (OSError, ValueError):
        return None
    for label, root in (("candidate", CANDIDATE_FILE.parent), ("p0", P0_FILE.parent)):
        try:
            return f"{label}/{resolved.relative_to(root).as_posix()}"
        except ValueError:
            pass
    return None


def install_audit_hook(accesses: list[str]) -> None:
    def audit(event: str, args: tuple[object, ...]) -> None:
        if event in FORBIDDEN_AUDIT_EVENTS or event.startswith(FORBIDDEN_AUDIT_PREFIXES):
            raise ForbiddenRuntimeEvent(event)
        if event == "open" and args:
            relative = relative_access(args[0])
            if relative is not None:
                accesses.append(relative)

    sys.addaudithook(audit)


def emission_record(stdout: io.StringIO, stderr: io.StringIO) -> dict[str, object]:
    stdout_bytes = stdout.getvalue().encode("utf-8")
    stderr_bytes = stderr.getvalue().encode("utf-8")
    return {
        "stdout_bytes": len(stdout_bytes),
        "stdout_sha256": sha256(stdout_bytes),
        "stderr_bytes": len(stderr_bytes),
        "stderr_sha256": sha256(stderr_bytes),
    }


def load_candidate() -> object:
    source = CANDIDATE_FILE.read_bytes()
    module = types.ModuleType("oia_candidate")
    module.__file__ = str(CANDIDATE_FILE)
    exec(compile(source, str(CANDIDATE_FILE), "exec"), module.__dict__)
    return module


def status_contract(module: object) -> tuple[dict[str, str], dict[str, str]]:
    by_symbol = {
        symbol: getattr(module, symbol)
        for symbol in ("RUNNING", "LEVEL_COMPLETED", "GAME_OVER")
    }
    if any(not isinstance(value, str) for value in by_symbol.values()):
        raise TypeError("candidate statuses must be strings")
    if len(set(by_symbol.values())) != 3:
        raise ValueError("candidate statuses must be distinct")
    return by_symbol, {value: symbol for symbol, value in by_symbol.items()}


def error_result(
    category: str,
    word: list[str],
    accesses: list[str],
    stdout: io.StringIO,
    stderr: io.StringIO,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "error",
        "error_category": category,
        "word": word,
        "file_accesses": accesses,
        "emissions": emission_record(stdout, stderr),
    }


def run(word: list[str]) -> dict[str, object]:
    accesses: list[str] = []
    stdout = io.StringIO()
    stderr = io.StringIO()
    install_audit_hook(accesses)
    try:
        initial_bytes = P0_FILE.read_bytes()
        initial_frame = load_ascii_frame(P0_FILE)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            module = load_candidate()
            _, status_by_value = status_contract(module)
            state = module.initial_state(initial_frame.copy())
            if not isinstance(state, dict):
                raise TypeError("initial_state must return a dictionary")
            rendered = module.render(state)
        replayed_bytes = encode_frame(rendered)
        p0 = {
            "frame_sha256": sha256(replayed_bytes),
            "matches_frame": replayed_bytes == initial_bytes,
            "status": "RUNNING",
        }
        if not p0["matches_frame"]:
            return {
                "schema_version": 1,
                "status": "replay_failure",
                "error_category": "p0_frame_mismatch",
                "p0": p0,
                "word": word,
                "steps": [],
                "file_accesses": accesses,
                "emissions": emission_record(stdout, stderr),
            }

        steps: list[dict[str, object]] = []
        terminal_status: str | None = None
        last_frame_sha256 = sha256(replayed_bytes)
        for action in word:
            if terminal_status is not None:
                steps.append(
                    {
                        "absorbed": True,
                        "action": action,
                        "final_frame_sha256": last_frame_sha256,
                        "status": terminal_status,
                    }
                )
                continue
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = module.step(state, action)
                if not isinstance(result, tuple) or len(result) != 2:
                    raise TypeError("step must return a two-tuple")
                state, raw_status = result
                if not isinstance(state, dict):
                    raise TypeError("step state must be a dictionary")
                rendered = module.render(state)
            if raw_status not in status_by_value:
                raise ValueError("step returned an undeclared status")
            status = status_by_value[raw_status]
            last_frame_sha256 = sha256(encode_frame(rendered))
            steps.append(
                {
                    "absorbed": False,
                    "action": action,
                    "final_frame_sha256": last_frame_sha256,
                    "status": status,
                }
            )
            if status in TERMINAL_SYMBOLS:
                terminal_status = status

        return {
            "schema_version": 1,
            "status": "pass",
            "error_category": None,
            "p0": p0,
            "word": word,
            "steps": steps,
            "file_accesses": accesses,
            "emissions": emission_record(stdout, stderr),
        }
    except ForbiddenRuntimeEvent:
        return error_result("forbidden_runtime_event", word, accesses, stdout, stderr)
    except BaseException as exc:
        return error_result(
            f"exception:{type(exc).__name__}", word, accesses, stdout, stderr
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--word-json", default="[]")
    args = parser.parse_args()
    try:
        word = json.loads(args.word_json)
        if not isinstance(word, list) or any(action not in VALID_ACTIONS for action in word):
            raise ValueError("invalid action word")
        if len(word) > 3:
            raise ValueError("action word exceeds frozen depth")
        result = run(word)
    except BaseException as exc:
        result = {
            "schema_version": 1,
            "status": "runner_error",
            "error_category": f"exception:{type(exc).__name__}",
        }
    print(canonical_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
