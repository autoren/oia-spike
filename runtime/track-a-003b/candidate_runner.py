#!/usr/bin/env python3
"""Fixed isolated adapter for one Track A 003b candidate and one action word."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import io
import json
import os
import sys
from pathlib import Path

import numpy as np


CANDIDATE_ROOT = Path("/candidate")
P0_ROOT = Path("/p0")
VALID_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
FORBIDDEN_AUDIT_PREFIXES = ("socket.", "subprocess.")
FORBIDDEN_AUDIT_EVENTS = {
    "os.system",
    "os.posix_spawn",
    "os.spawn",
    "pty.spawn",
}


class ForbiddenRuntimeEvent(PermissionError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_ascii_frame(path: Path) -> np.ndarray:
    rows = [
        [int(character, 16) for character in line.strip()]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("invalid P0 raster")
    return np.asarray(rows, dtype=np.int16)


def encode_frame(frame: object) -> bytes:
    array = np.asarray(frame)
    if array.ndim != 2:
        raise ValueError("renderer did not return a two-dimensional raster")
    rows: list[str] = []
    for row in array.tolist():
        if any(not isinstance(value, int) or value < 0 or value > 15 for value in row):
            raise ValueError("renderer returned a value outside the hexadecimal raster domain")
        rows.append("".join(format(value, "X") for value in row))
    return ("\n".join(rows) + "\n").encode("ascii")


def modeled_progress(state: object) -> dict[str, int]:
    if not isinstance(state, dict):
        return {}
    result: dict[str, int] = {}
    for key in ("level", "level_index", "levels_completed", "progress"):
        value = state.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            result[key] = value
    return result


def emission_record(stdout: io.StringIO, stderr: io.StringIO) -> dict[str, object]:
    stdout_bytes = stdout.getvalue().encode("utf-8")
    stderr_bytes = stderr.getvalue().encode("utf-8")
    return {
        "stdout_bytes": len(stdout_bytes),
        "stdout_sha256": sha256(stdout_bytes),
        "stderr_bytes": len(stderr_bytes),
        "stderr_sha256": sha256(stderr_bytes),
    }


def relative_access(path: object) -> str | None:
    if not isinstance(path, (str, bytes, os.PathLike)):
        return None
    try:
        resolved = Path(os.fsdecode(path)).resolve()
    except (OSError, ValueError):
        return None
    for label, root in (("candidate", CANDIDATE_ROOT), ("p0", P0_ROOT)):
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


def error_result(category: str, accesses: list[str], emissions: dict[str, object]) -> dict:
    return {
        "schema_version": 1,
        "status": "error",
        "error_category": category,
        "file_accesses": accesses,
        "emissions": emissions,
    }


def run(word: list[str]) -> dict:
    accesses: list[str] = []
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    install_audit_hook(accesses)
    try:
        metadata_bytes = (P0_ROOT / "initial_metadata.json").read_bytes()
        metadata = json.loads(metadata_bytes)
        initial_bytes = (P0_ROOT / "initial_frame.txt").read_bytes()
        initial_frame = load_ascii_frame(P0_ROOT / "initial_frame.txt")

        sys.path.insert(0, str(CANDIDATE_ROOT))
        with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
            state_io = importlib.import_module("world_model_state_io")
            engine_module = importlib.import_module("world_model_engine")
            status_module = importlib.import_module("game_status")
            state = state_io.initial_state_reconstruction(1, initial_frame.copy())
            replayed = np.asarray(state_io.state_renderer(state))

        replayed_bytes = encode_frame(replayed)
        p0 = {
            "frame_sha256": sha256(replayed_bytes),
            "metadata_sha256": sha256(metadata_bytes),
            "metadata": metadata,
            "matches_frame": replayed_bytes == initial_bytes,
            "status": status_module.RUNNING,
            "modeled_progress": modeled_progress(state),
        }
        if not p0["matches_frame"]:
            return {
                "schema_version": 1,
                "status": "replay_failure",
                "p0": p0,
                "word": word,
                "steps": [],
                "file_accesses": accesses,
                "emissions": emission_record(captured_stdout, captured_stderr),
            }

        steps: list[dict] = []
        game_status = status_module.RUNNING
        for action_name in word:
            with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
                state, game_status = engine_module.world_model_engine(
                    state, {"name": action_name}
                )
                rendered = state_io.state_renderer(state)
            steps.append(
                {
                    "action": action_name,
                    "final_frame_sha256": sha256(encode_frame(rendered)),
                    "status": game_status,
                    "modeled_progress": modeled_progress(state),
                    "error_category": None,
                }
            )
            if game_status != status_module.RUNNING:
                break

        return {
            "schema_version": 1,
            "status": "pass",
            "p0": p0,
            "word": word,
            "steps": steps,
            "file_accesses": accesses,
            "emissions": emission_record(captured_stdout, captured_stderr),
        }
    except ForbiddenRuntimeEvent:
        return error_result(
            "forbidden_runtime_event", accesses, emission_record(captured_stdout, captured_stderr)
        )
    except BaseException as exc:
        return error_result(
            f"exception:{type(exc).__name__}",
            accesses,
            emission_record(captured_stdout, captured_stderr),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--word-json", default="[]")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        word = json.loads(args.word_json)
        if not isinstance(word, list) or any(action not in VALID_ACTIONS for action in word):
            raise ValueError("invalid action word")
        if len(word) > 3:
            raise ValueError("action word exceeds frozen boundary")
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
