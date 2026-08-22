#!/usr/bin/env python3
"""Run the frozen post-outcome descriptive prediction-error diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
BEHAVIOR_RESULT = AUDIT_ROOT / "behavior-outcome" / "ADMISSION_AND_OIA_RESULT.json"
ARCHIVE_RESULT = AUDIT_ROOT / "archive-outcome" / "ARCHIVE_OUTCOME_RESULT.json"
ARCHIVE_EVIDENCE = AUDIT_ROOT / "archive-outcome" / "ARCHIVE_OUTCOME_EVIDENCE.zip"
DIAGNOSTIC_RUNNER = ROOT / "runtime" / "track-a-005a" / "prediction_diagnostic_runner.py"
EXPECTED_IMAGE_ID = "sha256:caee0dd1041ab150662d25fae1f47109fcc9aaaa9f51214cf83449e1309b5254"
EXPECTED_BEHAVIOR_SHA256 = "1fabd671dd0e396be5b493d27b7eac75313682ee3aef5cfb3fb03cdc580a4d77"
EXPECTED_ARCHIVE_RESULT_SHA256 = "06c2c44544545605de7955977702c03f23eaf1f52af1fd71d79b072cc8dac6d2"
EXPECTED_ARCHIVE_EVIDENCE_SHA256 = "e6de7cd8db997c561cfb4be078cc3437347af90f9c59e402761c7d790e3ed3a4"
CANDIDATES = ("C0006", "C0008")
SEEDS = (0, 1, 5, 10)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def parse_rows(rows: list[str]) -> list[list[int]]:
    if len(rows) != 64 or any(len(row) != 64 for row in rows):
        raise ValueError("raster is not 64x64")
    return [[int(character, 16) for character in row] for row in rows]


def frame_rows(payload: bytes) -> list[str]:
    rows = [row.upper() for row in payload.decode("ascii").splitlines()]
    parse_rows(rows)
    return rows


def descriptive_metrics(
    *,
    p0_rows: list[str],
    predicted_rows: list[str],
    actual_rows: list[str],
) -> dict[str, object]:
    p0 = parse_rows(p0_rows)
    predicted = parse_rows(predicted_rows)
    actual = parse_rows(actual_rows)
    mismatch = 0
    absolute_error = 0
    histogram_predicted = [0] * 16
    histogram_actual = [0] * 16
    predicted_delta: set[int] = set()
    actual_delta: set[int] = set()
    for y in range(64):
        for x in range(64):
            index = y * 64 + x
            left = predicted[y][x]
            right = actual[y][x]
            base = p0[y][x]
            mismatch += left != right
            absolute_error += abs(left - right)
            histogram_predicted[left] += 1
            histogram_actual[right] += 1
            if left != base:
                predicted_delta.add(index)
            if right != base:
                actual_delta.add(index)
    intersection = predicted_delta & actual_delta
    union = predicted_delta | actual_delta
    return {
        "pixel_mismatch_count": mismatch,
        "pixel_match_count": 4096 - mismatch,
        "pixel_accuracy_fraction": {"numerator": 4096 - mismatch, "denominator": 4096},
        "absolute_color_error_fraction": {"numerator": absolute_error, "denominator": 4096},
        "color_histogram_l1": sum(abs(a - b) for a, b in zip(histogram_predicted, histogram_actual)),
        "predicted_delta_pixel_count": len(predicted_delta),
        "actual_delta_pixel_count": len(actual_delta),
        "delta_intersection_count": len(intersection),
        "delta_union_count": len(union),
        "delta_jaccard_fraction": {
            "numerator": len(intersection),
            "denominator": len(union),
        },
    }


def docker_image_id(image: str) -> str:
    completed = subprocess.run(
        ("docker", "image", "inspect", image, "--format", "{{.Id}}"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def run_candidate(image: str, candidate: Path, p0: Path, seed: int) -> dict[str, object]:
    command = (
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--memory=512m",
        "--cpus=1",
        "--pids-limit=64",
        "--user=65532:65532",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=16777216",
        "--env",
        f"PYTHONHASHSEED={seed}",
        "--mount",
        f"type=bind,src={candidate},dst=/candidate,readonly",
        "--mount",
        f"type=bind,src={p0},dst=/p0,readonly",
        "--mount",
        f"type=bind,src={DIAGNOSTIC_RUNNER},dst=/diagnostic/prediction_diagnostic_runner.py,readonly",
        "--entrypoint",
        "python",
        image,
        "-I",
        "/diagnostic/prediction_diagnostic_runner.py",
    )
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
    )
    if completed.stderr:
        raise RuntimeError("diagnostic container emitted stderr")
    return json.loads(completed.stdout)


def run(prepared_root: Path, image: str, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"diagnostic output exists: {output}")
    if docker_image_id(image) != EXPECTED_IMAGE_ID:
        raise ValueError("diagnostic runtime image changed")
    if sha256_file(BEHAVIOR_RESULT) != EXPECTED_BEHAVIOR_SHA256:
        raise ValueError("behavior result changed")
    if sha256_file(ARCHIVE_RESULT) != EXPECTED_ARCHIVE_RESULT_SHA256:
        raise ValueError("archive outcome result changed")
    if sha256_file(ARCHIVE_EVIDENCE) != EXPECTED_ARCHIVE_EVIDENCE_SHA256:
        raise ValueError("archive outcome evidence changed")

    behavior = json.loads(BEHAVIOR_RESULT.read_text(encoding="utf-8"))
    archive_result = json.loads(ARCHIVE_RESULT.read_text(encoding="utf-8"))
    actual_hashes = {row["observation"]["final_frame_sha256"] for row in archive_result["outcomes"]}
    if len(actual_hashes) != 1:
        raise ValueError("archival actual frames do not agree")
    actual_hash = next(iter(actual_hashes))
    run_root = archive_result["matching_run_roots"][0]
    with zipfile.ZipFile(ARCHIVE_EVIDENCE) as archive:
        actual_rows = frame_rows(archive.read(f"runs/{run_root}/step_0001_final.txt"))
    actual_bytes = ("\n".join(actual_rows) + "\n").encode("ascii")
    if sha256_bytes(actual_bytes) != actual_hash:
        raise ValueError("actual frame bytes changed")
    p0_rows = frame_rows((AUDIT_ROOT / "p0" / "initial_frame.txt").read_bytes())

    expected_predictions = archive_result["candidate_predictions"]
    records = []
    for candidate_id in CANDIDATES:
        candidate_root = prepared_root / "candidates" / candidate_id
        rendered = [run_candidate(image, candidate_root, prepared_root / "p0", seed) for seed in SEEDS]
        if any(row != rendered[0] for row in rendered[1:]):
            raise ValueError(f"diagnostic raster changed across seeds: {candidate_id}")
        primary = rendered[0]
        if primary["status"] != "pass" or primary["p0_rows_equal_input"] is not True:
            raise ValueError(f"diagnostic candidate failed: {candidate_id}")
        expected = expected_predictions[candidate_id]
        if (
            primary["final_frame_sha256"] != expected["final_frame_sha256"]
            or primary["predicted_status"] != expected["status"]
        ):
            raise ValueError(f"diagnostic raster disagrees with prospective trace: {candidate_id}")
        records.append(
            {
                "candidate_id": candidate_id,
                "predicted_frame_sha256": primary["final_frame_sha256"],
                "predicted_status": primary["predicted_status"],
                "final_frame_rows": primary["final_frame_rows"],
                "cross_seed_exact": True,
                "pythonhashseed_values": list(SEEDS),
                "metrics": descriptive_metrics(
                    p0_rows=p0_rows,
                    predicted_rows=primary["final_frame_rows"],
                    actual_rows=actual_rows,
                ),
            }
        )
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "classification": "post_outcome_retrospective_error_diagnostic",
        "actual_frame_sha256": actual_hash,
        "actual_status": "RUNNING",
        "p0_frame_sha256": sha256_bytes(("\n".join(p0_rows) + "\n").encode("ascii")),
        "persistence_baseline": descriptive_metrics(
            p0_rows=p0_rows, predicted_rows=p0_rows, actual_rows=actual_rows
        ),
        "candidate_records": records,
        "execution_accounting": {
            "candidate_processes": len(CANDIDATES) * len(SEEDS),
            "oia_processes": 0,
            "real_arc_actions": 0,
            "later_step_payloads_read": 0,
            "model_or_api_calls": 0,
            "network_or_service_calls": 0,
        },
        "interpretation_rule": (
            "Report descriptive distances and the persistence baseline only. No "
            "post-hoc tolerance, pass threshold, or change to the prospective verdict."
        ),
        "claim_boundary": (
            "Retrospective error characterization after the archival outcome was "
            "opened; it cannot strengthen the prospective separator claim."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(pretty_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.prepared_root.resolve(), args.image, args.output.resolve())
    print(
        json.dumps(
            {
                "candidate_processes": result["execution_accounting"]["candidate_processes"],
                "classification": result["classification"],
                "pixel_mismatch_by_candidate": {
                    row["candidate_id"]: row["metrics"]["pixel_mismatch_count"]
                    for row in result["candidate_records"]
                },
                "persistence_pixel_mismatch": result["persistence_baseline"]["pixel_mismatch_count"],
                "result_sha256": sha256_file(args.output.resolve()),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
