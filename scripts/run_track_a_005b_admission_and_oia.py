#!/usr/bin/env python3
"""Calibrate revised candidates, admit a fixed frontier, and select the next action."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
sys.path.insert(0, str(ROOT / "scripts"))
import run_track_a_005a_admission_and_oia as base


ACTIONS = base.ACTIONS
HORIZON = base.HORIZON
SEEDS = base.SEEDS
REPETITIONS = base.REPETITIONS
EMPTY_SHA256 = base.EMPTY_SHA256
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
EXPECTED_P1_SHA256 = "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"


def canonical_bytes(value: object) -> bytes:
    return base.canonical_bytes(value)


def pretty_bytes(value: object) -> bytes:
    return base.pretty_bytes(value)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def frozen_words() -> list[tuple[str, ...]]:
    return base.frozen_words()


def behavior_projection(result: Mapping[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in ("status", "error_category", "p0", "calibration", "word", "steps")
        if key in result
    }


def valid_pass(result: Mapping[str, object], word: tuple[str, ...]) -> bool:
    emissions = result.get("emissions", {})
    accesses = result.get("file_accesses", [])
    calibration = result.get("calibration", {})
    p0 = result.get("p0", {})
    return (
        result.get("status") == "pass"
        and result.get("error_category") is None
        and result.get("word") == list(word)
        and isinstance(result.get("steps"), list)
        and len(result["steps"]) == len(word)
        and p0.get("matches_frame") is True
        and p0.get("frame_sha256") == EXPECTED_P0_SHA256
        and calibration.get("action") == "ACTION6"
        and calibration.get("matches_frame") is True
        and calibration.get("final_frame_sha256") == EXPECTED_P1_SHA256
        and calibration.get("status") == "RUNNING"
        and emissions.get("stdout_bytes") == 0
        and emissions.get("stderr_bytes") == 0
        and emissions.get("stdout_sha256") == EMPTY_SHA256
        and emissions.get("stderr_sha256") == EMPTY_SHA256
        and set(accesses)
        <= {
            "candidate/candidate.py",
            "calibration/p0.txt",
            "calibration/p1_settled.txt",
        }
    )


def docker_image_id(image: str) -> str:
    completed = subprocess.run(
        ("docker", "image", "inspect", image, "--format", "{{.Id}}"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def run_once(
    *,
    image: str,
    candidate: Path,
    calibration: Path,
    word: tuple[str, ...],
    seed: int,
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
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
        f"type=bind,src={calibration},dst=/calibration,readonly",
        image,
        "--word-json",
        json.dumps(word, separators=(",", ":")),
    )
    accounting["candidate_processes"] += 1
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_category": "timeout", "word": list(word)}
    if completed.returncode != 0:
        return {
            "status": "error",
            "error_category": f"container_exit:{completed.returncode}",
            "stderr_bytes": len(completed.stderr),
            "stderr_sha256": sha256_bytes(completed.stderr),
            "word": list(word),
        }
    try:
        result = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "error",
            "error_category": "invalid_runner_output",
            "stdout_bytes": len(completed.stdout),
            "stdout_sha256": sha256_bytes(completed.stdout),
            "word": list(word),
        }
    result["container_stderr_bytes"] = len(completed.stderr)
    result["container_stderr_sha256"] = sha256_bytes(completed.stderr)
    return result


def load_prepared(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest_path = root / "PREPARED_BUNDLES.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "revision_bundles_prepared_behavior_not_run":
        raise ValueError("revision preparation did not produce a frontier")
    candidates = [
        row
        for row in manifest["candidate_records"]
        if row["status"] == "prepared_not_imported_or_executed"
    ]
    candidate_ids = [row["candidate_id"] for row in candidates]
    if len(candidate_ids) < 2 or candidate_ids != sorted(candidate_ids):
        raise ValueError("prepared revision identity or order changed")
    for row in candidates:
        path = root / "candidates" / row["candidate_id"] / "candidate.py"
        if sha256_file(path) != row["candidate_sha256"]:
            raise ValueError(f"prepared candidate hash changed: {row['candidate_id']}")
    for name, expected in (
        ("p0.txt", EXPECTED_P0_SHA256),
        ("p1_settled.txt", EXPECTED_P1_SHA256),
    ):
        if sha256_file(root / "calibration" / name) != expected:
            raise ValueError(f"prepared calibration changed: {name}")
    return manifest, candidates


def calibration_stage(
    image: str,
    root: Path,
    candidates: Sequence[Mapping[str, object]],
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
    records = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        observed = run_once(
            image=image,
            candidate=root / "candidates" / candidate_id,
            calibration=root / "calibration",
            word=(),
            seed=0,
            timeout_seconds=timeout_seconds,
            accounting=accounting,
        )
        records.append(
            {
                "candidate_id": candidate_id,
                "pass": valid_pass(observed, ()),
                "trace": behavior_projection(observed),
            }
        )
    return {"stage": "exact_p0_p1_calibration", "records": records}


def provisional_stage(
    image: str,
    root: Path,
    candidates: Sequence[Mapping[str, object]],
    calibration_stage_result: Mapping[str, object],
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
    calibrated = {
        row["candidate_id"] for row in calibration_stage_result["records"] if row["pass"]
    }
    signature_owner: dict[str, str] = {}
    records = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in calibrated:
            records.append({"candidate_id": candidate_id, "status": "not_run_calibration_failed"})
            continue
        word_records = []
        all_pass = True
        for word in frozen_words():
            observed = run_once(
                image=image,
                candidate=root / "candidates" / candidate_id,
                calibration=root / "calibration",
                word=word,
                seed=0,
                timeout_seconds=timeout_seconds,
                accounting=accounting,
            )
            projected = behavior_projection(observed)
            all_pass = all_pass and valid_pass(observed, word)
            word_records.append({"word": list(word), "trace": projected})
        signature = sha256_bytes(canonical_bytes(word_records))
        owner = signature_owner.setdefault(signature, candidate_id) if all_pass else None
        records.append(
            {
                "candidate_id": candidate_id,
                "status": (
                    "provisionally_unique"
                    if all_pass and owner == candidate_id
                    else "behavioral_duplicate"
                    if all_pass
                    else "provisional_execution_failure"
                ),
                "duplicate_of": None if owner in (None, candidate_id) else owner,
                "trace_signature_sha256": signature,
                "word_records": word_records,
            }
        )
    return {
        "stage": "provisional_post_p1",
        "seed": 0,
        "word_count": len(frozen_words()),
        "records": records,
        "provisionally_unique": [
            row["candidate_id"] for row in records if row["status"] == "provisionally_unique"
        ],
    }


def full_stage(
    image: str,
    root: Path,
    candidates: Sequence[Mapping[str, object]],
    provisional: Mapping[str, object],
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
    by_id = {str(row["candidate_id"]): row for row in candidates}
    records = []
    for candidate_id in provisional["provisionally_unique"]:
        candidate = by_id[candidate_id]
        word_records = []
        deterministic = True
        all_pass = True
        for word in frozen_words():
            repetitions = []
            for seed in SEEDS:
                for repetition in REPETITIONS:
                    observed = run_once(
                        image=image,
                        candidate=root / "candidates" / candidate_id,
                        calibration=root / "calibration",
                        word=word,
                        seed=seed,
                        timeout_seconds=timeout_seconds,
                        accounting=accounting,
                    )
                    projected = behavior_projection(observed)
                    all_pass = all_pass and valid_pass(observed, word)
                    repetitions.append(
                        {"seed": seed, "repetition": repetition, "trace": projected}
                    )
            hashes = sorted(
                {sha256_bytes(canonical_bytes(row["trace"])) for row in repetitions}
            )
            word_deterministic = len(hashes) == 1
            deterministic = deterministic and word_deterministic
            word_records.append(
                {
                    "word": list(word),
                    "deterministic": word_deterministic,
                    "trace_sha256": hashes,
                    "repetitions": repetitions,
                }
            )
        records.append(
            {
                "candidate_id": candidate_id,
                "candidate_sha256": candidate["candidate_sha256"],
                "all_words_pass": all_pass,
                "deterministic": deterministic,
                "word_records": word_records,
            }
        )
    return {
        "stage": "full_post_p1",
        "seeds": list(SEEDS),
        "repetitions_per_seed": len(REPETITIONS),
        "word_count": len(frozen_words()),
        "records": records,
        "admitted_candidates": [
            row["candidate_id"]
            for row in records
            if row["all_words_pass"] and row["deterministic"]
        ],
    }


def blocker_verdict(
    calibration: Mapping[str, object],
    provisional: Mapping[str, object],
    full: Mapping[str, object],
) -> str:
    if sum(1 for row in calibration["records"] if row["pass"]) < 2:
        return "revision_generation_or_calibration_blocker"
    if len(provisional["provisionally_unique"]) < 2:
        return "no_revised_behavioral_divergence"
    if len(full["admitted_candidates"]) < 2:
        return "nondeterministic_or_runtime_blocker"
    return "revision_frontier_feasible"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    args = parser.parse_args()

    prepared_root = args.prepared_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"outcome root exists: {output_root}")
    image_id = docker_image_id(args.image)
    if image_id != args.expected_image_id:
        raise ValueError("runtime image ID changed")
    _, candidates = load_prepared(prepared_root)
    output_root.mkdir(parents=True)
    accounting = {
        "candidate_processes": 0,
        "oia_processes": 0,
        "step_2_or_later_payloads_read": 0,
        "network_or_service_calls": 0,
        "model_or_api_calls": 0,
        "credential_uses": 0,
        "private_or_sealed_evaluations": 0,
        "real_arc_actions": 0,
    }
    calibration = calibration_stage(
        args.image, prepared_root, candidates, args.timeout_seconds, accounting
    )
    provisional = provisional_stage(
        args.image,
        prepared_root,
        candidates,
        calibration,
        args.timeout_seconds,
        accounting,
    )
    full = full_stage(
        args.image,
        prepared_root,
        candidates,
        provisional,
        args.timeout_seconds,
        accounting,
    )
    verdict = blocker_verdict(calibration, provisional, full)
    adapter_validation = None
    selected_next_action = None
    adaptive_depth = None
    oia_hashes = None
    oia_report_sha256 = None
    if verdict == "revision_frontier_feasible":
        payload, adapter_validation = base.build_adapter(full)
        payload_path = output_root / "OIA_INPUT.json"
        payload_path.write_bytes(pretty_bytes(payload))
        report_bytes, oia_hashes = base.run_oia(payload_path, accounting)
        report = json.loads(report_bytes)
        sys.path.insert(0, str(BASELINE_SRC))
        from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

        system = CandidateSystem.from_dict(payload)
        adaptive = report["full_candidate_identification"]["adaptive"]
        try:
            adaptive_depth = verify_serialized_adaptive_result(system, adaptive)
        except Exception:
            verdict = "oia_blocker"
        else:
            policy = adaptive.get("policy") or {}
            if (
                adaptive.get("status") != "solved"
                or adaptive.get("exact") is not True
                or adaptive.get("enumeration_complete") is not True
                or adaptive.get("optimality_certified") is not True
                or adaptive.get("depth_claim") != "minimum"
                or policy.get("type") != "action"
                or policy.get("action") not in ACTIONS
                or adaptive_depth != adaptive.get("worst_case_steps")
            ):
                verdict = "oia_blocker"
            else:
                selected_next_action = policy["action"]
                verdict = "revised_separator_selected_pre_step2"
        (output_root / "OIA_REPORT.json").write_bytes(report_bytes)
        (output_root / "ADAPTER_VALIDATION.json").write_bytes(
            pretty_bytes(adapter_validation)
        )
        oia_report_sha256 = sha256_bytes(report_bytes)

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005b",
        "gate_verdict": verdict,
        "runtime_image_id": image_id,
        "prepared_bundles_sha256": sha256_file(prepared_root / "PREPARED_BUNDLES.json"),
        "stages": {
            "calibration": calibration,
            "provisional": provisional,
            "full": full,
        },
        "adapter_validation": adapter_validation,
        "selected_next_action": selected_next_action,
        "adaptive_minimum_worst_case_depth": adaptive_depth,
        "oia_report_sha256": oia_report_sha256,
        "cross_process_oia_report_sha256": oia_hashes,
        "p1_persistence_baseline": {
            "definition": "Predict the exact settled P1 raster and RUNNING status after every next action.",
            "p1_sha256": EXPECTED_P1_SHA256,
            "evaluated_against_step2": False,
        },
        "execution_accounting": accounting,
        "epistemic_ordering": {
            "revision_generation_rules_merged_before_inference": True,
            "revision_package_merged_before_source_open": True,
            "runner_adapter_and_oia_path_merged_before_candidate_source_open": True,
            "selected_next_action_merged_before_step2_access_required": True,
            "step_2_or_later_payloads_read": 0,
        },
        "claim_boundary": (
            "Opened Track A intervention-triggered calibration, revised frontier admission, "
            "and exact OIA next-action selection before step-2 access. Calibration is not "
            "prediction; no step-2 result, real ARC action, sealed transfer, or Track B claim."
        ),
    }
    (output_root / "ADMISSION_AND_OIA_RESULT.json").write_bytes(pretty_bytes(result))
    print(
        json.dumps(
            {
                "admitted": len(full["admitted_candidates"]),
                "candidate_processes": accounting["candidate_processes"],
                "gate_verdict": verdict,
                "oia_processes": accounting["oia_processes"],
                "selected_next_action": selected_next_action,
                "result_sha256": sha256_file(output_root / "ADMISSION_AND_OIA_RESULT.json"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
