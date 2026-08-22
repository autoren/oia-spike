#!/usr/bin/env python3
"""Open only matching public ACTION7 step-2 archival outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR_RESULT = ROOT / "audits" / "track-a-005c" / "behavior-outcome" / "ADMISSION_AND_OIA_RESULT.json"
EXPECTED_BEHAVIOR_RESULT_SHA256 = "e177ee9bbf86d0d88faee64915858beb22ff87518e7d83b32cb0f110b6e9a840"
EXPECTED_ARCHIVE_SHA256 = "c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93"
EXPECTED_ARCHIVE_SIZE = 797_835_543
TARGET_ACTION = "ACTION7"
P1_PERSISTENCE = {
    "final_frame_sha256": "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140",
    "status": "RUNNING",
}
RUN_ROOTS = (
    "ewma_v1.5_sv_gpt-5.5_xhigh_run1",
    "ewma_v1.6_sv_gpt-5.6-sol_max_run1",
    "ewma_v1.6_sv_gpt-5.6-sol_xhigh_run1",
    "twma_v1.6_gpt-5.6-sol_max_run1",
    "twma_v1.6_gpt-5.6-sol_xhigh_run1",
)
FULL_BASENAMES = (
    "step_0002_final.png",
    "step_0002_final.txt",
    "step_0002_intermediate_00.png",
    "step_0002_intermediate_00.txt",
    "step_0002_intermediate_01.png",
    "step_0002_intermediate_01.txt",
    "step_0002_intermediate_02.png",
    "step_0002_intermediate_02.txt",
    "step_0002_intermediate_03.png",
    "step_0002_intermediate_03.txt",
    "step_0002_metadata.json",
)
SHORT_BASENAMES = (
    "step_0002_final.png",
    "step_0002_final.txt",
    "step_0002_metadata.json",
)
EXPECTED_BASENAMES = {
    RUN_ROOTS[0]: FULL_BASENAMES,
    RUN_ROOTS[1]: FULL_BASENAMES,
    RUN_ROOTS[2]: SHORT_BASENAMES,
    RUN_ROOTS[3]: FULL_BASENAMES,
    RUN_ROOTS[4]: FULL_BASENAMES,
}
STATE_TO_STATUS = {
    "NOT_FINISHED": "RUNNING",
    "LEVEL_COMPLETED": "LEVEL_COMPLETED",
    "WON": "LEVEL_COMPLETED",
    "GAME_OVER": "GAME_OVER",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def member_path(run_root: str, basename: str) -> str:
    return (
        f"runs_additional/{run_root}/su15/run/agent_run/client/session/"
        f"level_01_attempt_01/{basename}"
    )


def header_inventory(archive: Path) -> tuple[int, dict[str, list[str]]]:
    total = 0
    observed = {run: [] for run in RUN_ROOTS}
    seen: set[str] = set()
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            total += 1
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe archive member: {member.name}")
            if member.name in seen:
                raise ValueError(f"duplicate archive member: {member.name}")
            seen.add(member.name)
            for run in RUN_ROOTS:
                prefix = member_path(run, "step_0002_")
                if member.name.startswith(prefix):
                    if not member.isfile():
                        raise ValueError(f"step-2 member is not a file: {member.name}")
                    observed[run].append(member.name)
                    break
    for run in RUN_ROOTS:
        expected = {member_path(run, basename) for basename in EXPECTED_BASENAMES[run]}
        if set(observed[run]) != expected:
            raise ValueError(f"step-2 header set changed: {run}")
    return total, observed


def read_exact_members(archive: Path, names: set[str]) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            if member.name not in names:
                continue
            handle = stream.extractfile(member)
            if handle is None:
                raise ValueError(f"target payload unavailable: {member.name}")
            result[member.name] = handle.read()
    if set(result) != names:
        raise ValueError("not every exact target payload was read")
    return result


def validate_frame(value: bytes) -> str:
    text = value.decode("ascii")
    lines = text.splitlines()
    if len(lines) != 64 or any(len(line) != 64 for line in lines):
        raise ValueError("settled frame is not a 64x64 raster")
    if any(character not in "0123456789ABCDEFabcdef" for line in lines for character in line):
        raise ValueError("settled frame is not hexadecimal")
    canonical = ("\n".join(line.upper() for line in lines) + "\n").encode("ascii")
    return sha256_bytes(canonical)


def candidate_predictions() -> dict[str, dict[str, str]]:
    if sha256_file(BEHAVIOR_RESULT) != EXPECTED_BEHAVIOR_RESULT_SHA256:
        raise ValueError("prospective ACTION7 result pin changed")
    result = json.loads(BEHAVIOR_RESULT.read_text(encoding="utf-8"))
    if (
        result["gate_verdict"] != "maintenance_revised_separator_selected_pre_step2"
        or result["selected_next_action"] != TARGET_ACTION
        or result["execution_accounting"]["step_2_or_later_payloads_read"] != 0
    ):
        raise ValueError("prospective ACTION7 boundary changed")
    predictions = {}
    full = result["stages"]["full"]
    for candidate in full["records"]:
        if candidate["candidate_id"] not in full["admitted_candidates"]:
            continue
        record = next(row for row in candidate["word_records"] if row["word"] == [TARGET_ACTION])
        traces = [row["trace"] for row in record["repetitions"]]
        if any(trace != traces[0] for trace in traces[1:]):
            raise ValueError("candidate ACTION7 prediction is not deterministic")
        step = traces[0]["steps"][0]
        predictions[candidate["candidate_id"]] = {
            "final_frame_sha256": step["final_frame_sha256"],
            "status": step["status"],
        }
    if len(predictions) != 3 or len({tuple(sorted(row.items())) for row in predictions.values()}) != 3:
        raise ValueError("ACTION7 does not distinguish the merged candidate frontier")
    return predictions


def deterministic_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100444 << 16
            archive.writestr(info, files[name])


def verdict_for(outcomes: list[dict[str, object]]) -> str:
    if not outcomes:
        return "no_matching_recorded_step2_action"
    observations = {json.dumps(row["observation"], sort_keys=True) for row in outcomes}
    if len(observations) != 1:
        return "recorded_step2_outcome_inconsistent_across_runs"
    matches = {tuple(row["matching_candidates"]) for row in outcomes}
    baselines = {row["matches_persistence_baseline"] for row in outcomes}
    if len(matches) != 1 or len(baselines) != 1:
        return "recorded_step2_outcome_inconsistent_across_runs"
    candidate_matches = next(iter(matches))
    persistence = next(iter(baselines))
    if len(candidate_matches) == 1 and persistence:
        return "revised_step2_matches_candidate_and_persistence"
    if len(candidate_matches) == 1:
        return "revised_step2_matches_one_candidate"
    if persistence:
        return "revised_step2_matches_persistence_only"
    return "revised_step2_outside_candidate_frontier_and_persistence"


def extract(archive: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"output exists: {output_root}")
    if archive.stat().st_size != EXPECTED_ARCHIVE_SIZE or sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("source archive identity changed")
    predictions = candidate_predictions()
    header_count, headers = header_inventory(archive)
    metadata_names = {member_path(run, "step_0002_metadata.json") for run in RUN_ROOTS}
    metadata_payloads = read_exact_members(archive, metadata_names)
    package_files: dict[str, bytes] = {}
    metadata_records = []
    matching_runs = []
    for run in RUN_ROOTS:
        name = member_path(run, "step_0002_metadata.json")
        payload = metadata_payloads[name]
        metadata = json.loads(payload)
        action_id = metadata["action_input"]["id"]
        if not isinstance(action_id, str):
            raise ValueError(f"recorded step-2 action is not a string: {run}")
        if action_id == TARGET_ACTION:
            matching_runs.append(run)
        package_files[f"runs/{run}/step_0002_metadata.json"] = payload
        metadata_records.append(
            {
                "run_root": run,
                "member": name,
                "action_id": action_id,
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )

    selected_names = {
        member_path(run, basename)
        for run in matching_runs
        for basename in EXPECTED_BASENAMES[run]
        if basename != "step_0002_metadata.json"
    }
    selected_payloads = read_exact_members(archive, selected_names) if selected_names else {}
    outcomes = []
    for run in matching_runs:
        metadata = json.loads(metadata_payloads[member_path(run, "step_0002_metadata.json")])
        state = metadata["state"]
        status = STATE_TO_STATUS.get(state)
        if status is None:
            raise ValueError(f"unsupported recorded state: {state}")
        files = []
        for basename in EXPECTED_BASENAMES[run]:
            name = member_path(run, basename)
            payload = metadata_payloads[name] if basename.endswith("metadata.json") else selected_payloads[name]
            package_files[f"runs/{run}/{basename}"] = payload
            files.append(
                {
                    "basename": basename,
                    "member": name,
                    "sha256": sha256_bytes(payload),
                    "size_bytes": len(payload),
                }
            )
        observation = {
            "final_frame_sha256": validate_frame(
                selected_payloads[member_path(run, "step_0002_final.txt")]
            ),
            "status": status,
        }
        outcomes.append(
            {
                "run_root": run,
                "recorded_state": state,
                "observation": observation,
                "matching_candidates": [
                    candidate for candidate, prediction in predictions.items() if prediction == observation
                ],
                "matches_persistence_baseline": observation == P1_PERSISTENCE,
                "files": files,
                "intermediate_frame_pairs_preserved": sum(
                    1 for basename in EXPECTED_BASENAMES[run] if "intermediate_" in basename and basename.endswith(".txt")
                ),
            }
        )

    output_root.mkdir(parents=True)
    evidence_path = output_root / "STEP2_ARCHIVE_OUTCOME_EVIDENCE.zip"
    deterministic_zip(evidence_path, package_files)
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005d",
        "gate_verdict": verdict_for(outcomes),
        "classification": "public_archival_prospective_step2_outcome",
        "target_action": TARGET_ACTION,
        "candidate_predictions": predictions,
        "persistence_baseline": P1_PERSISTENCE,
        "metadata_records": metadata_records,
        "matching_run_roots": matching_runs,
        "outcomes": outcomes,
        "header_inventory": {
            "archive_member_headers_scanned": header_count,
            "headers": headers,
            "run_roots": list(RUN_ROOTS),
        },
        "evidence_package": {
            "path": "STEP2_ARCHIVE_OUTCOME_EVIDENCE.zip",
            "sha256": sha256_file(evidence_path),
            "size_bytes": evidence_path.stat().st_size,
            "file_count": len(package_files),
        },
        "access_accounting": {
            "step2_metadata_payloads_read": len(metadata_payloads),
            "matching_action_nonmetadata_payloads_read": len(selected_payloads),
            "nonmatching_run_frame_payloads_read": 0,
            "step3_or_later_payloads_read": 0,
            "candidate_processes": 0,
            "oia_processes": 0,
            "model_or_api_calls": 0,
            "real_arc_actions": 0,
        },
        "claim_boundary": "Public archival prospective step-2 outcome for merged maintenance-repaired ACTION7 only; no live action, untouched-model, sealed-transfer, decision-value, or Track B claim.",
    }
    (output_root / "STEP2_ARCHIVE_OUTCOME_RESULT.json").write_bytes(pretty_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.archive.resolve(), args.output_root.resolve())
    print(
        json.dumps(
            {
                "gate_verdict": result["gate_verdict"],
                "matching_runs": len(result["matching_run_roots"]),
                "result_sha256": sha256_file(
                    args.output_root.resolve() / "STEP2_ARCHIVE_OUTCOME_RESULT.json"
                ),
                "target_action": result["target_action"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
