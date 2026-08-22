#!/usr/bin/env python3
"""Extract only the selected Track A 005a reset packets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
from typing import Mapping

from inventory_track_a_005a_source import (
    EXPECTED_ARCHIVE_MD5,
    EXPECTED_ARCHIVE_SHA256,
    EXPECTED_ARCHIVE_SIZE,
    EXPECTED_RUNS,
    P0_FILENAMES,
    file_hashes,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
SELECTION_PATH = AUDIT_ROOT / "SOURCE_UNIVERSE_SELECTION.json"
EXPECTED_SELECTION_SHA256 = "c7d6b17f0ed24811fef433899d3806afd4e22b1ba103c6ace5bbcae5080dbc3b"
EXPECTED_GAME = "su15"
MAX_FILE_BYTES = {
    "initial_frame.png": 2 * 1024 * 1024,
    "initial_frame.txt": 2 * 1024 * 1024,
    "initial_metadata.json": 64 * 1024,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_selection() -> Mapping[str, object]:
    if sha256_file(SELECTION_PATH) != EXPECTED_SELECTION_SHA256:
        raise ValueError("held-out source selection hash changed")
    payload = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    if payload["selection"]["selected_game"] != EXPECTED_GAME:
        raise ValueError("held-out selected game changed")
    return payload


def selected_targets(selection: Mapping[str, object]) -> dict[str, tuple[str, str]]:
    raw_paths = selection["selection"]["selected_p0_paths"]
    targets: dict[str, tuple[str, str]] = {}
    for run in EXPECTED_RUNS:
        if run not in raw_paths:
            raise ValueError(f"selected P0 paths omit run: {run}")
        for filename in P0_FILENAMES:
            member_name = str(raw_paths[run][filename])
            if member_name in targets:
                raise ValueError(f"duplicate selected P0 path: {member_name}")
            targets[member_name] = (run, filename)
    if len(targets) != len(EXPECTED_RUNS) * len(P0_FILENAMES):
        raise ValueError("selected P0 target count changed")
    return targets


def read_exact_targets(
    archive_path: Path,
    targets: Mapping[str, tuple[str, str]],
) -> dict[tuple[str, str], bytes]:
    found: dict[tuple[str, str], bytes] = {}
    seen_names: set[str] = set()
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive:
            if member.name not in targets:
                continue
            if member.name in seen_names:
                raise ValueError(f"duplicate selected tar member: {member.name}")
            seen_names.add(member.name)
            if not member.isfile():
                raise ValueError(f"selected P0 member is not regular: {member.name}")
            run, filename = targets[member.name]
            if member.size < 1 or member.size > MAX_FILE_BYTES[filename]:
                raise ValueError(f"selected P0 member exceeds size boundary: {member.name}")
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"could not read selected P0 member: {member.name}")
            data = handle.read(MAX_FILE_BYTES[filename] + 1)
            if len(data) != member.size:
                raise ValueError(f"selected P0 member size mismatch: {member.name}")
            found[(run, filename)] = data
    missing = set(targets.values()) - set(found)
    if missing:
        raise ValueError(f"selected P0 members missing: {sorted(missing)}")
    return found


def validate_common_p0(
    values: Mapping[tuple[str, str], bytes],
) -> tuple[dict[str, bytes], dict[str, object]]:
    canonical: dict[str, bytes] = {}
    equality: dict[str, object] = {}
    for filename in P0_FILENAMES:
        by_run = {run: values[(run, filename)] for run in EXPECTED_RUNS}
        hashes = {run: sha256_bytes(data) for run, data in by_run.items()}
        unique = sorted(set(hashes.values()))
        if len(unique) != 1:
            raise ValueError(f"selected P0 {filename} differs across runs")
        canonical[filename] = by_run[EXPECTED_RUNS[0]]
        equality[filename] = {
            "all_five_byte_identical": True,
            "sha256": unique[0],
            "size_bytes": len(canonical[filename]),
            "per_run_sha256": hashes,
        }

    png = canonical["initial_frame.png"]
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("canonical initial_frame.png lacks the PNG signature")
    try:
        text = canonical["initial_frame.txt"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical initial_frame.txt is not UTF-8") from exc
    lines = text.splitlines()
    if not lines or any(not line for line in lines):
        raise ValueError("canonical text frame is empty or ragged")
    widths = {len(line) for line in lines}
    if len(widths) != 1:
        raise ValueError("canonical text frame has inconsistent row widths")

    try:
        metadata = json.loads(canonical["initial_metadata.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("canonical initial metadata is not UTF-8 JSON") from exc
    if not isinstance(metadata, Mapping):
        raise ValueError("canonical initial metadata must be an object")
    action_input = metadata.get("action_input")
    if not isinstance(action_input, Mapping) or action_input.get("id") != "RESET":
        raise ValueError("canonical P0 is not a reset packet")
    actions = metadata.get("available_actions")
    if (
        not isinstance(actions, list)
        or not actions
        or any(not isinstance(item, int) or isinstance(item, bool) for item in actions)
        or len(actions) != len(set(actions))
    ):
        raise ValueError("canonical P0 action alphabet is invalid")
    if metadata.get("step_index") != 0:
        raise ValueError("canonical P0 step_index is not zero")

    validation = {
        "frame_text": {
            "encoding": "UTF-8",
            "height": len(lines),
            "width": widths.pop(),
            "rectangular": True,
        },
        "frame_png": {"png_signature_valid": True},
        "metadata": {
            "reset_action": True,
            "available_actions": actions,
            "step_index": metadata["step_index"],
            "top_level_keys": sorted(metadata),
        },
    }
    return canonical, {"file_equality": equality, "content_validation": validation}


def write_outputs(
    values: Mapping[tuple[str, str], bytes],
    canonical: Mapping[str, bytes],
    destination: Path,
    canonical_destination: Path,
) -> None:
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists() or partial.exists():
        raise FileExistsError("P0 extraction destination already exists")
    if canonical_destination.exists():
        raise FileExistsError("canonical P0 destination already exists")
    partial.mkdir(parents=True)
    for (run, filename), data in values.items():
        run_dir = partial / run
        run_dir.mkdir(exist_ok=True)
        (run_dir / filename).write_bytes(data)
    os.replace(partial, destination)

    canonical_destination.mkdir(parents=True)
    for filename, data in canonical.items():
        path = canonical_destination / filename
        path.write_bytes(data)
        path.chmod(0o444)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--canonical-destination", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archive = args.archive.resolve()
    destination = args.destination.resolve()
    canonical_destination = args.canonical_destination.resolve()
    evidence = args.evidence.resolve()
    if evidence.exists():
        raise FileExistsError("P0 extraction evidence already exists")
    observed_archive = file_hashes(archive)
    expected_archive = (
        EXPECTED_ARCHIVE_SIZE,
        EXPECTED_ARCHIVE_MD5,
        EXPECTED_ARCHIVE_SHA256,
    )
    if observed_archive != expected_archive:
        raise ValueError("source archive identity changed")
    selection = load_selection()
    targets = selected_targets(selection)
    values = read_exact_targets(archive, targets)
    canonical, validation = validate_common_p0(values)
    write_outputs(values, canonical, destination, canonical_destination)

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "status": "selected_common_p0_extracted_and_validated",
        "selected_game": EXPECTED_GAME,
        "selection_sha256": EXPECTED_SELECTION_SHA256,
        "archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "target_member_count": len(targets),
        "target_member_paths": sorted(targets),
        "validation": validation,
        "canonical_files": {
            filename: {
                "path": str((canonical_destination / filename).relative_to(ROOT)),
                "sha256": sha256_bytes(data),
                "size_bytes": len(data),
            }
            for filename, data in sorted(canonical.items())
        },
        "access_accounting": {
            "selected_p0_payloads_read": len(targets),
            "nonselected_member_payloads_read": 0,
            "candidate_files_read": 0,
            "behavioral_traces_read": 0,
            "scores_read": 0,
            "candidate_processes": 0,
            "model_or_api_calls": 0,
            "oia_processes": 0,
            "real_arc_actions": 0,
        },
        "claim_boundary": (
            "Selected common reset P0 extraction only; no candidate, behavior, "
            "score, model, OIA, or real environment action."
        ),
    }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "audit_id": result["audit_id"],
                "canonical_hashes": {
                    name: record["sha256"] for name, record in result["canonical_files"].items()
                },
                "selected_game": EXPECTED_GAME,
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
