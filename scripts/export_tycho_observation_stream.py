#!/usr/bin/env python3
"""Export the lossless observation stream from a patched Tycho game record.

This is a credential-free packaging utility. It does not import Tycho, execute a
model, instantiate an ARC environment, replay an action, or inspect private game
source. Legacy records fail closed because they lack the logging-only fields
added by integrations/tycho/trace-capture-v0.1.patch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_record(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Tycho game record {path}: {exc}") from exc
    _require(isinstance(record, dict), "Tycho game-record root must be an object")
    _require(record.get("partial") is False, "partial Tycho game record is not exportable")
    trace = record.get("trace")
    _require(isinstance(trace, list) and trace, "Tycho game record has no trace")
    return record


def _grid_digest(grid: Any, label: str) -> str:
    _require(isinstance(grid, list) and grid, f"{label}: grid is missing")
    _require(all(isinstance(row, list) and row for row in grid), f"{label}: grid rows are invalid")
    payload = json.dumps(grid, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def observation_for_step(step: Any, index: int) -> dict[str, Any]:
    label = f"trace[{index}]"
    _require(isinstance(step, dict), f"{label}: step is not an object")
    turn = step.get("turn")
    action = step.get("action")
    _require(isinstance(turn, int) and turn >= 0, f"{label}: invalid turn")
    _require(isinstance(action, str) and action, f"{label}: action missing")
    pre_action = step.get("pre_action_frame")
    returned = step.get("returned_frames")
    available = step.get("available_actions_before")
    result_frame = step.get("frame")
    _grid_digest(pre_action, f"{label}:pre_action_frame")
    _require(isinstance(returned, list) and returned, f"{label}: returned_frames missing")
    returned_hashes = {
        _grid_digest(grid, f"{label}:returned_frames[{frame_index}]")
        for frame_index, grid in enumerate(returned)
    }
    _require(
        _grid_digest(result_frame, f"{label}:frame") in returned_hashes,
        f"{label}: result frame is not present in returned frame sequence",
    )
    _require(
        isinstance(available, list) and all(isinstance(value, str) for value in available),
        f"{label}: available_actions_before missing",
    )
    state = step.get("state")
    levels = step.get("levels_completed")
    _require(isinstance(state, str), f"{label}: external state missing")
    _require(isinstance(levels, int) and levels >= 0, f"{label}: levels_completed invalid")

    reasoning = step.get("reasoning")
    _require(isinstance(reasoning, dict), f"{label}: reasoning missing")
    for field in ("llm_calls", "tool_trace", "workspace"):
        _require(field in reasoning, f"{label}: reasoning lacks {field}")
    workspace = reasoning.get("workspace")
    _require(isinstance(workspace, dict), f"{label}: workspace snapshot missing")
    _require(
        isinstance(workspace.get("snapshot_schema"), int)
        and workspace["snapshot_schema"] >= 2,
        f"{label}: workspace snapshot is not schema 2",
    )

    return {
        "turn": turn,
        "action": action,
        "pre_action_frame": pre_action,
        "returned_frames": returned,
        "available_actions_before": available,
        "external_state_after": state,
        "levels_completed_after": levels,
        "reset_boundary": action == "RESET",
        "animation_boundary": len(returned) > 1,
    }


def export_observation_stream(record_path: Path, output_path: Path, *, force: bool = False) -> dict[str, Any]:
    record_path = record_path.resolve()
    output_path = output_path.resolve()
    _require(record_path != output_path, "output must differ from the source game record")
    _require(force or not output_path.exists(), f"output already exists: {output_path}")
    record = _load_record(record_path)
    observations = [
        observation_for_step(step, index)
        for index, step in enumerate(record["trace"])
    ]
    turns = [item["turn"] for item in observations]
    _require(
        all(current > previous for previous, current in zip(turns, turns[1:])),
        "trace turns are not strictly increasing",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
        for item in observations
    )
    output_path.write_text(payload, encoding="utf-8")
    return {
        "status": "tycho_observation_stream_exported",
        "game_id": record.get("game_id"),
        "record_sha256": sha256(record_path),
        "observation_stream_sha256": sha256(output_path),
        "steps": len(observations),
        "resets": sum(item["reset_boundary"] for item in observations),
        "animation_boundaries": sum(item["animation_boundary"] for item in observations),
        "model_calls": 0,
        "environment_actions": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = export_observation_stream(args.record, args.output, force=args.force)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{result['status']}: {result['steps']} steps, "
            f"{result['animation_boundaries']} animation boundaries"
        )


if __name__ == "__main__":
    main()
