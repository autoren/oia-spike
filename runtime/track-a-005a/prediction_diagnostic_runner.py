#!/usr/bin/env python3
"""Retrospectively emit one generated candidate's settled ACTION6 raster."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import types

import numpy as np


CANDIDATE_FILE = Path("/candidate/candidate.py")
P0_FILE = Path("/p0/initial_frame.txt")


def load_frame(path: Path) -> np.ndarray:
    rows = [[int(character, 16) for character in line] for line in path.read_text().splitlines()]
    if len(rows) != 64 or any(len(row) != 64 for row in rows):
        raise ValueError("P0 is not 64x64")
    return np.asarray(rows, dtype=np.int16)


def encode_frame(value: object) -> tuple[list[str], str]:
    array = np.asarray(value)
    if array.shape != (64, 64):
        raise ValueError("candidate frame is not 64x64")
    rows = []
    for row in array.tolist():
        if any(not isinstance(pixel, int) or pixel < 0 or pixel > 15 for pixel in row):
            raise ValueError("candidate frame is outside the hexadecimal domain")
        rows.append("".join(format(pixel, "X") for pixel in row))
    payload = ("\n".join(rows) + "\n").encode("ascii")
    return rows, hashlib.sha256(payload).hexdigest()


def load_candidate() -> object:
    source = CANDIDATE_FILE.read_bytes()
    module = types.ModuleType("oia_candidate_diagnostic")
    module.__file__ = str(CANDIDATE_FILE)
    exec(compile(source, str(CANDIDATE_FILE), "exec"), module.__dict__)
    return module


def main() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        p0 = load_frame(P0_FILE)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            module = load_candidate()
            statuses = {
                getattr(module, symbol): symbol
                for symbol in ("RUNNING", "LEVEL_COMPLETED", "GAME_OVER")
            }
            state = module.initial_state(p0.copy())
            initial_rows, initial_hash = encode_frame(module.render(state))
            state, raw_status = module.step(state, "ACTION6")
            rows, frame_hash = encode_frame(module.render(state))
        if raw_status not in statuses:
            raise ValueError("candidate returned an undeclared status")
        result = {
            "schema_version": 1,
            "status": "pass",
            "action": "ACTION6",
            "p0_frame_sha256": initial_hash,
            "p0_rows_equal_input": initial_rows == ["".join(format(int(pixel), "X") for pixel in row) for row in p0.tolist()],
            "final_frame_sha256": frame_hash,
            "final_frame_rows": rows,
            "predicted_status": statuses[raw_status],
            "emissions": {
                "stdout_bytes": len(stdout.getvalue().encode("utf-8")),
                "stderr_bytes": len(stderr.getvalue().encode("utf-8")),
            },
        }
    except BaseException as exc:
        result = {
            "schema_version": 1,
            "status": "error",
            "error_category": f"exception:{type(exc).__name__}",
        }
    print(json.dumps(result, allow_nan=False, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
