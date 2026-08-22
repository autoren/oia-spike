#!/usr/bin/env python3
"""Preflight and, only with explicit authorization, run Track A 005e locally."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005e"
PROTOCOL_PATH = AUDIT_ROOT / "LOCAL_OUTCOME_PROTOCOL.frozen.json"
ACQUISITION_PATH = AUDIT_ROOT / "OFFICIAL_SOURCE_ACQUISITION.json"
DEFAULT_SOURCE = ROOT / "local-work" / "track-a-005e" / "acquired-su15" / "source.response.py"
DEFAULT_METADATA = ROOT / "local-work" / "track-a-005e" / "acquired-su15" / "metadata.response.json"
EXPECTED_SOURCE_SHA256 = "a5f91f7c963d6ca6447dae0ab21342b48a3f511601c40dfa8e972bdc59b4651e"
EXPECTED_METADATA_SHA256 = "666da4c4a84cdee0c0b0a3f3b6b12d1aacecc14ddb1f4cb3be712b83aad63114"
EXPECTED_005C_RESULT_SHA256 = "e177ee9bbf86d0d88faee64915858beb22ff87518e7d83b32cb0f110b6e9a840"
EXPECTED_005C_PACKAGE_SHA256 = "bd28d94d3a22becd7e63cd19395a34124d4cd1ab8e546cc370615b55c8dffe45"
EXPECTED_005D_RESULT_SHA256 = "d09a71682086dd0871d1035948f7f0091f86139148086d2676321a850bb219c5"
EXPECTED_IMPORTS = {"arcengine", "numpy", "typing"}
EXPECTED_CLASSES = ["cqrtilsbtt", "Su15"]
EXPECTED_PACKAGES = {
    "annotated-types": "0.7.0",
    "arcengine": "0.9.3",
    "numpy": "2.4.1",
    "pydantic": "2.12.5",
    "pydantic-core": "2.41.5",
    "typing-extensions": "4.15.0",
    "typing-inspection": "0.4.2",
}
STATE_MAP = {"NOT_FINISHED": "RUNNING", "WIN": "SUCCESS", "GAME_OVER": "FAIL"}
HEX = "0123456789ABCDEF"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def read_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status_at_freeze"] != "frozen_after_source_acquisition_before_source_execution_reset_or_action":
        raise ValueError("005e prospective ordering changed")
    if protocol["frozen_parent"]["selected_next_action"] != "ACTION7":
        raise ValueError("005e target action changed")
    return protocol


def source_structure(source: bytes) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".", 1)[0])
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    return {"imports": sorted(imports), "top_level_classes": classes}


def preflight(source_path: Path, metadata_path: Path, *, check_runtime: bool) -> dict[str, Any]:
    protocol = read_protocol()
    acquisition = json.loads(ACQUISITION_PATH.read_text(encoding="utf-8"))
    source = source_path.read_bytes()
    metadata_raw = metadata_path.read_bytes()
    source_hash = sha256_bytes(source)
    metadata_hash = sha256_bytes(metadata_raw)
    if source_hash != EXPECTED_SOURCE_SHA256 or source_hash != protocol["environment"]["source_sha256"]:
        raise ValueError("005e source hash mismatch")
    if metadata_hash != EXPECTED_METADATA_SHA256 or metadata_hash != protocol["environment"]["metadata_sha256"]:
        raise ValueError("005e metadata hash mismatch")
    if acquisition["source"]["sha256"] != source_hash:
        raise ValueError("005e acquisition/source mismatch")
    parent_paths = {
        "track_a_005c_result": (
            ROOT / "audits/track-a-005c/behavior-outcome/ADMISSION_AND_OIA_RESULT.json",
            EXPECTED_005C_RESULT_SHA256,
        ),
        "track_a_005c_candidate_package": (
            ROOT / "audits/track-a-005c/normalization-result/NORMALIZED_CANDIDATE_PACKAGE.zip",
            EXPECTED_005C_PACKAGE_SHA256,
        ),
        "track_a_005d_result": (
            ROOT / "audits/track-a-005d/step2-outcome/STEP2_ARCHIVE_OUTCOME_RESULT.json",
            EXPECTED_005D_RESULT_SHA256,
        ),
    }
    for label, (path, expected) in parent_paths.items():
        if sha256_file(path) != expected:
            raise ValueError(f"005e frozen parent changed: {label}")
    metadata = json.loads(metadata_raw)
    if metadata != {
        "game_id": "su15-1944f8ab",
        "title": "SU15",
        "default_fps": 20,
        "tags": ["click"],
        "baseline_actions": [22, 42, 26, 115, 36, 31, 8, 40, 41],
    }:
        raise ValueError("005e official metadata changed")
    if not source.startswith(b"# MIT License\n"):
        raise ValueError("005e source license header changed")
    structure = source_structure(source)
    if set(structure["imports"]) != EXPECTED_IMPORTS or structure["top_level_classes"] != EXPECTED_CLASSES:
        raise ValueError("005e source structure changed")

    observed_packages: dict[str, str] = {}
    if check_runtime:
        if platform.python_version() != "3.12.12":
            raise ValueError("005e Python version mismatch")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise ValueError("005e runtime must be macOS arm64")
        for package, expected in EXPECTED_PACKAGES.items():
            observed = importlib.metadata.version(package)
            if observed != expected:
                raise ValueError(f"005e package mismatch: {package}={observed}, expected {expected}")
            observed_packages[package] = observed
    return {
        "audit_id": "OIA-1-TRACK-A-005e",
        "metadata_sha256": metadata_hash,
        "parent_sha256": {label: expected for label, (_path, expected) in parent_paths.items()},
        "packages": observed_packages,
        "pass": True,
        "source_executed": False,
        "source_sha256": source_hash,
        "source_structure": structure,
        "status": "local_source_preflight_passed",
    }


def frame_to_text(frame: Any) -> str:
    if getattr(frame, "shape", None) != (64, 64):
        raise ValueError(f"unexpected frame shape: {getattr(frame, 'shape', None)}")
    rows: list[str] = []
    for row in frame.tolist():
        if any(not isinstance(pixel, int) or not 0 <= pixel <= 15 for pixel in row):
            raise ValueError("frame contains a non-hex pixel")
        rows.append("".join(HEX[pixel] for pixel in row))
    return "\n".join(rows) + "\n"


def observation(frame_data: Any) -> dict[str, Any]:
    frames = [frame_to_text(frame) for frame in frame_data.frame]
    if not frames:
        raise ValueError("environment returned no frames")
    state = frame_data.state.value
    if state not in STATE_MAP:
        raise ValueError(f"unexpected state: {state}")
    return {
        "available_actions": list(frame_data.available_actions),
        "final_frame_sha256": sha256_bytes(frames[-1].encode("ascii")),
        "frame_count": len(frames),
        "frame_sha256": [sha256_bytes(frame.encode("ascii")) for frame in frames],
        "frames": frames,
        "raw_state": state,
        "status": STATE_MAP[state],
    }


def disable_network() -> None:
    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("network disabled by Track A 005e")

    socket.socket = blocked  # type: ignore[assignment]
    socket.create_connection = blocked  # type: ignore[assignment]


def worker(source_path: Path, metadata_path: Path, x: int, y: int, repetition: int) -> dict[str, Any]:
    protocol = read_protocol()
    preflight(source_path, metadata_path, check_runtime=True)
    from arcengine import ActionInput, GameAction

    disable_network()
    namespace: dict[str, Any] = {
        "__file__": source_path.as_posix(),
        "__name__": "oia_track_a_005e_su15",
    }
    source = source_path.read_bytes()
    exec(compile(source, source_path.as_posix(), "exec"), namespace)
    game_class = namespace.get("Su15")
    if not isinstance(game_class, type):
        raise ValueError("official Su15 class missing after source execution")
    game = game_class(seed=0)
    run: dict[str, Any] = {
        "coordinate": {"x": x, "y": y},
        "repetition": repetition,
        "seed": 0,
    }
    p0 = observation(game.perform_action(ActionInput(id=GameAction.RESET, data={}), raw=True))
    run["reset"] = p0
    if (
        p0["final_frame_sha256"] != protocol["exact_reproduction"]["p0_final_frame_sha256"]
        or p0["status"] != "RUNNING"
        or p0["available_actions"] != [6, 7]
    ):
        run["stopped_after"] = "RESET"
        return run
    p1 = observation(
        game.perform_action(
            ActionInput(id=GameAction.ACTION6, data={"x": x, "y": y}), raw=True
        )
    )
    run["action6"] = p1
    if (
        p1["final_frame_sha256"] != protocol["exact_reproduction"]["p1_final_frame_sha256"]
        or p1["status"] != "RUNNING"
        or p1["available_actions"] != [6, 7]
    ):
        run["stopped_after"] = "ACTION6"
        return run
    run["action7"] = observation(
        game.perform_action(ActionInput(id=GameAction.ACTION7, data={}), raw=True)
    )
    run["stopped_after"] = "ACTION7"
    return run


def public_observation(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "frames"}


def result_verdict(runs: list[dict[str, Any]], protocol: dict[str, Any]) -> tuple[str, list[str]]:
    if any(run["stopped_after"] == "RESET" for run in runs):
        return "local_p0_reproduction_blocker", []
    if any(run["stopped_after"] == "ACTION6" for run in runs):
        return "local_p1_reproduction_blocker", []
    observed = {
        (run["action7"]["final_frame_sha256"], run["action7"]["status"])
        for run in runs
    }
    if len(observed) != 1:
        return "local_action7_nondeterminism_or_hidden_path_dependence", []
    final_hash, status = next(iter(observed))
    matches = [
        candidate
        for candidate, prediction in protocol["candidate_predictions"].items()
        if prediction == {"final_frame_sha256": final_hash, "status": status}
    ]
    if len(matches) == 1:
        return "local_action7_matches_one_candidate", matches
    if len(matches) > 1:
        return "local_action7_realized_outcome_not_discriminating", matches
    return "local_action7_outside_candidate_frontier", []


def add_zip_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100444 << 16
    archive.writestr(info, payload)


def write_evidence(path: Path, runs: list[dict[str, Any]]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for run in runs:
            coordinate = run["coordinate"]
            root = f"runs/x{coordinate['x']:02d}_y{coordinate['y']:02d}/r{run['repetition']:02d}"
            metadata = {
                "coordinate": coordinate,
                "repetition": run["repetition"],
                "seed": run["seed"],
                "stopped_after": run["stopped_after"],
            }
            for phase in ("reset", "action6", "action7"):
                if phase not in run:
                    continue
                value = run[phase]
                metadata[phase] = public_observation(value)
                for index, frame in enumerate(value["frames"]):
                    add_zip_bytes(archive, f"{root}/{phase}/frame_{index:04d}.txt", frame.encode("ascii"))
            add_zip_bytes(archive, f"{root}/metadata.json", pretty_bytes(metadata))


def run_driver(source_path: Path, metadata_path: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    protocol = read_protocol()
    preflight_result = preflight(source_path, metadata_path, check_runtime=True)
    destination.mkdir(parents=True)
    runs: list[dict[str, Any]] = []
    for coordinate in protocol["action_schedule"]["ordered_coordinates"]:
        for repetition in range(1, protocol["action_schedule"]["repetitions_per_coordinate"] + 1):
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--source",
                str(source_path.resolve()),
                "--metadata",
                str(metadata_path.resolve()),
                "--worker",
                "--authorize-local-actions",
                "--x",
                str(coordinate["x"]),
                "--y",
                str(coordinate["y"]),
                "--repetition",
                str(repetition),
            ]
            environment = dict(os.environ)
            environment.update({"PYTHONHASHSEED": "0", "NO_PROXY": "*", "no_proxy": "*"})
            environment.pop("ARC_API_KEY", None)
            completed = subprocess.run(command, check=True, capture_output=True, text=True, env=environment)
            runs.append(json.loads(completed.stdout))
    verdict, matches = result_verdict(runs, protocol)
    evidence_path = destination / "LOCAL_OUTCOME_EVIDENCE.zip"
    write_evidence(evidence_path, runs)
    public_runs = []
    for run in runs:
        public_run = {key: value for key, value in run.items() if key not in {"reset", "action6", "action7"}}
        for phase in ("reset", "action6", "action7"):
            if phase in run:
                public_run[phase] = public_observation(run[phase])
        public_runs.append(public_run)
    result = {
        "access_accounting": {
            "action6_interventions": sum("action6" in run for run in runs),
            "action7_interventions": sum("action7" in run for run in runs),
            "candidate_processes": 0,
            "model_or_service_calls": 0,
            "oia_processes": 0,
            "resets": len(runs),
        },
        "audit_id": "OIA-1-TRACK-A-005e",
        "claim_boundary": protocol["claim_boundary"],
        "evidence_package": {
            "path": evidence_path.name,
            "sha256": sha256_file(evidence_path),
            "size_bytes": evidence_path.stat().st_size,
        },
        "gate_verdict": verdict,
        "matching_candidates": matches,
        "preflight": preflight_result,
        "runs": public_runs,
        "schema_version": 1,
        "target_action": "ACTION7",
    }
    (destination / "LOCAL_OUTCOME_RESULT.json").write_bytes(pretty_bytes(result))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--authorize-local-actions", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--x", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--y", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--repetition", type=int, help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.preflight_only:
        print(json.dumps(preflight(args.source, args.metadata, check_runtime=True), sort_keys=True))
        return
    if not args.authorize_local_actions:
        raise SystemExit("refusing to reset or act without --authorize-local-actions")
    if args.worker:
        if args.x is None or args.y is None or args.repetition is None:
            raise SystemExit("worker coordinates and repetition are required")
        print(json.dumps(worker(args.source, args.metadata, args.x, args.y, args.repetition), sort_keys=True))
        return
    if args.output is None:
        raise SystemExit("--output is required for an authorized outcome run")
    print(json.dumps(run_driver(args.source, args.metadata, args.output.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
