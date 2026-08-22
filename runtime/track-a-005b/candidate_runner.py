#!/usr/bin/env python3
"""Isolated runner for exact P0->P1 calibration then one bounded action word."""

from __future__ import annotations

import argparse
import contextlib
import copy  # noqa: F401 - preloaded permitted candidate import.
import hashlib
import io
import json
import math  # noqa: F401 - preloaded permitted candidate import.
import os
from pathlib import Path
import sys
import types
import typing  # noqa: F401 - preloaded permitted candidate import.

import numpy as np


CANDIDATE_FILE = Path("/candidate/candidate.py")
P0_FILE = Path("/calibration/p0.txt")
P1_FILE = Path("/calibration/p1_settled.txt")
CALIBRATION_ACTION = "ACTION6"
VALID_ACTIONS = ("ACTION6", "ACTION7")
TERMINAL_SYMBOLS = ("LEVEL_COMPLETED", "GAME_OVER")
FORBIDDEN_AUDIT_PREFIXES = ("ctypes.", "multiprocessing.", "socket.", "subprocess.")
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


def load_ascii_frame(path: Path) -> tuple[np.ndarray, bytes]:
    raw = path.read_bytes()
    rows = [
        [int(character, 16) for character in line.strip()]
        for line in raw.decode("ascii").splitlines()
        if line.strip()
    ]
    if len(rows) != 64 or any(len(row) != 64 for row in rows):
        raise ValueError("calibration frame must be a 64x64 hexadecimal raster")
    return np.asarray(rows, dtype=np.int16), raw


def encode_frame(frame: object) -> bytes:
    array = np.asarray(frame)
    if array.shape != (64, 64):
        raise ValueError("renderer must return a 64x64 raster")
    rows = []
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
    for label, root in (
        ("candidate", CANDIDATE_FILE.parent),
        ("calibration", P0_FILE.parent),
    ):
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
    out = stdout.getvalue().encode("utf-8")
    err = stderr.getvalue().encode("utf-8")
    return {
        "stdout_bytes": len(out),
        "stdout_sha256": sha256(out),
        "stderr_bytes": len(err),
        "stderr_sha256": sha256(err),
    }


def load_candidate() -> object:
    source = CANDIDATE_FILE.read_bytes()
    module = types.ModuleType("oia_revision_candidate")
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


def advance(module: object, state: dict[str, object], action: str) -> tuple[dict[str, object], str, bytes]:
    result = module.step(state, action)
    if not isinstance(result, tuple) or len(result) != 2:
        raise TypeError("step must return a two-tuple")
    next_state, raw_status = result
    if not isinstance(next_state, dict):
        raise TypeError("step state must be a dictionary")
    return next_state, raw_status, encode_frame(module.render(next_state))


def run(word: list[str]) -> dict[str, object]:
    accesses: list[str] = []
    stdout = io.StringIO()
    stderr = io.StringIO()
    install_audit_hook(accesses)
    try:
        p0_frame, p0_bytes = load_ascii_frame(P0_FILE)
        _, p1_bytes = load_ascii_frame(P1_FILE)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            module = load_candidate()
            _, status_by_value = status_contract(module)
            state = module.initial_state(p0_frame.copy())
            if not isinstance(state, dict):
                raise TypeError("initial_state must return a dictionary")
            replayed = encode_frame(module.render(state))
        p0 = {
            "frame_sha256": sha256(replayed),
            "matches_frame": replayed == p0_bytes,
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
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            state, raw_status, calibrated = advance(module, state, CALIBRATION_ACTION)
        if raw_status not in status_by_value:
            raise ValueError("calibration returned an undeclared status")
        calibration = {
            "action": CALIBRATION_ACTION,
            "final_frame_sha256": sha256(calibrated),
            "matches_frame": calibrated == p1_bytes,
            "status": status_by_value[raw_status],
        }
        if not calibration["matches_frame"] or calibration["status"] != "RUNNING":
            return {
                "schema_version": 1,
                "status": "calibration_failure",
                "error_category": (
                    "p1_frame_mismatch"
                    if not calibration["matches_frame"]
                    else "p1_status_mismatch"
                ),
                "p0": p0,
                "calibration": calibration,
                "word": word,
                "steps": [],
                "file_accesses": accesses,
                "emissions": emission_record(stdout, stderr),
            }

        steps: list[dict[str, object]] = []
        terminal_status: str | None = None
        last_hash = sha256(calibrated)
        for action in word:
            if terminal_status is not None:
                steps.append(
                    {
                        "absorbed": True,
                        "action": action,
                        "final_frame_sha256": last_hash,
                        "status": terminal_status,
                    }
                )
                continue
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                state, raw_status, frame = advance(module, state, action)
            if raw_status not in status_by_value:
                raise ValueError("step returned an undeclared status")
            status = status_by_value[raw_status]
            last_hash = sha256(frame)
            steps.append(
                {
                    "absorbed": False,
                    "action": action,
                    "final_frame_sha256": last_hash,
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
            "calibration": calibration,
            "word": word,
            "steps": steps,
            "file_accesses": accesses,
            "emissions": emission_record(stdout, stderr),
        }
    except ForbiddenRuntimeEvent:
        return error_result("forbidden_runtime_event", word, accesses, stdout, stderr)
    except BaseException as exc:
        return error_result(f"exception:{type(exc).__name__}", word, accesses, stdout, stderr)


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
