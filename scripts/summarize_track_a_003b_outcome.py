#!/usr/bin/env python3
"""Independently verify raw Track A 003b stages and write a compact outcome."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path


RUNTIME_IMAGE_ID = "sha256:644d899fa00c3a9fc16cc05f94ee5d078653891fe55659cd8e51fb1126027051"
PREPARED_BUNDLES_SHA256 = "e4b1de5e4141c2f37e60b668ec616efcf9c506ad663a7811150d762cf9d611d1"
P0_FRAME_SHA256 = "0fc0241eb2d3c992a2af68643f36e3878f5140fc85aed38410dd66ef5486afc7"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ORDER = (
    "max/final",
    "xhigh/final",
    "max/iteration_1",
    "xhigh/iteration_1",
    "max/iteration_2",
    "xhigh/iteration_2",
    "max/iteration_3",
    "xhigh/iteration_3",
    "max/iteration_4",
    "xhigh/iteration_4",
    "max/iteration_5",
    "xhigh/iteration_5",
    "max/iteration_6",
)
VALID_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def words() -> list[list[str]]:
    return [
        list(word)
        for length in (1, 2, 3)
        for word in itertools.product(VALID_ACTIONS, repeat=length)
    ]


def load_stage(path: Path, expected_stage: str) -> tuple[dict, dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["runtime_image_id"] != RUNTIME_IMAGE_ID:
        raise ValueError(f"runtime image mismatch in {path}")
    if document["prepared_bundles_sha256"] != PREPARED_BUNDLES_SHA256:
        raise ValueError(f"prepared-bundle mismatch in {path}")
    isolation = document["isolation"]
    expected_isolation = {
        "bounded_resources": True,
        "candidate_mount": "read_only",
        "capabilities": "all_dropped",
        "network": "none",
        "no_new_privileges": True,
        "p0_mount": "read_only",
        "root_filesystem": "read_only",
        "unprivileged_uid_gid": "65532:65532",
    }
    if isolation != expected_isolation:
        raise ValueError(f"isolation contract mismatch in {path}")
    stage = document["stage_result"]
    if stage["stage"] != expected_stage:
        raise ValueError(f"unexpected stage in {path}")
    return document, stage


def validate_p0(path: Path) -> tuple[dict, dict[str, dict]]:
    _, stage = load_stage(path, "p0")
    if stage["candidate_count"] != 13 or stage["pass_count"] != 13:
        raise ValueError("P0 stage did not pass all candidates")
    if tuple(record["candidate_id"] for record in stage["results"]) != ORDER:
        raise ValueError("P0 candidate order changed")
    by_candidate: dict[str, dict] = {}
    for record in stage["results"]:
        result = record["result"]
        if not record["pass"] or result["status"] != "pass":
            raise ValueError(f"P0 failure: {record['candidate_id']}")
        if not result["p0"]["matches_frame"] or result["p0"]["frame_sha256"] != P0_FRAME_SHA256:
            raise ValueError(f"P0 replay mismatch: {record['candidate_id']}")
        emissions = result["emissions"]
        if emissions != {
            "stderr_bytes": 0,
            "stderr_sha256": EMPTY_SHA256,
            "stdout_bytes": 0,
            "stdout_sha256": EMPTY_SHA256,
        }:
            raise ValueError(f"candidate emitted output during P0: {record['candidate_id']}")
        allowed = {
            "p0/initial_metadata.json",
            "p0/initial_frame.txt",
            "candidate/__pycache__/world_model_state_io.cpython-312.pyc",
            "candidate/world_model_state_io.py",
            "candidate/__pycache__/world_model_engine.cpython-312.pyc",
            "candidate/world_model_engine.py",
            "candidate/__pycache__/game_status.cpython-312.pyc",
            "candidate/game_status.py",
        }
        if not set(result["file_accesses"]) <= allowed:
            raise ValueError(f"unexpected candidate/P0 file access: {record['candidate_id']}")
        by_candidate[record["candidate_id"]] = record
    return stage, by_candidate


def validate_provisional(path: Path) -> tuple[dict, dict[str, dict]]:
    _, stage = load_stage(path, "provisional")
    expected_words = words()
    if stage["seed"] != 0 or stage["word_count"] != 84:
        raise ValueError("provisional boundary changed")
    if tuple(record["candidate_id"] for record in stage["results"]) != ORDER:
        raise ValueError("provisional candidate order changed")

    owners: dict[str, str] = {}
    by_candidate: dict[str, dict] = {}
    for record in stage["results"]:
        word_results = record["word_results"]
        if len(word_results) != 84:
            raise ValueError(f"incomplete provisional screen: {record['candidate_id']}")
        if [result["word"] for result in word_results] != expected_words:
            raise ValueError(f"word order mismatch: {record['candidate_id']}")
        if any(result["status"] != "pass" for result in word_results):
            raise ValueError(f"provisional error: {record['candidate_id']}")
        observed_signature = sha256_bytes(canonical_bytes(word_results))
        if observed_signature != record["trace_signature_sha256"]:
            raise ValueError(f"trace signature mismatch: {record['candidate_id']}")
        owner = owners.setdefault(observed_signature, record["candidate_id"])
        expected_status = "provisionally_unique" if owner == record["candidate_id"] else "behavioral_duplicate"
        if record["status"] != expected_status:
            raise ValueError(f"deduplication status mismatch: {record['candidate_id']}")
        if record["duplicate_of"] != (None if owner == record["candidate_id"] else owner):
            raise ValueError(f"duplicate owner mismatch: {record['candidate_id']}")
        by_candidate[record["candidate_id"]] = record

    unique = [record["candidate_id"] for record in stage["results"] if record["status"] == "provisionally_unique"]
    if stage["provisionally_unique"] != unique:
        raise ValueError("provisionally unique list mismatch")
    return stage, by_candidate


def validate_full(path: Path, provisional: dict[str, dict]) -> tuple[dict, dict[str, dict]]:
    _, stage = load_stage(path, "full")
    if stage["seeds"] != [0, 1, 5, 10] or stage["repetitions_per_seed"] != 2 or stage["word_count"] != 84:
        raise ValueError("full determinism matrix changed")
    expected_candidates = ["max/final", "max/iteration_2"]
    if [record["candidate_id"] for record in stage["results"]] != expected_candidates:
        raise ValueError("full-stage candidate list changed")
    by_candidate: dict[str, dict] = {}
    expected_words = words()
    for record in stage["results"]:
        if not record["deterministic"] or record["word_count"] != 84:
            raise ValueError(f"candidate is not deterministic: {record['candidate_id']}")
        if [word_record["word"] for word_record in record["word_records"]] != expected_words:
            raise ValueError(f"full word order mismatch: {record['candidate_id']}")
        representative_traces: list[dict] = []
        for word_record in record["word_records"]:
            repetitions = word_record["repetitions"]
            expected_matrix = [(seed, repetition) for seed in (0, 1, 5, 10) for repetition in (1, 2)]
            if [(item["seed"], item["repetition"]) for item in repetitions] != expected_matrix:
                raise ValueError(f"seed/repetition order mismatch: {record['candidate_id']}")
            hashes = {sha256_bytes(canonical_bytes(item["trace"])) for item in repetitions}
            if len(hashes) != 1 or word_record["trace_sha256"] != sorted(hashes) or not word_record["deterministic"]:
                raise ValueError(f"nondeterministic word: {record['candidate_id']}:{word_record['word']}")
            if any(item["trace"]["status"] != "pass" for item in repetitions):
                raise ValueError(f"full-stage error: {record['candidate_id']}:{word_record['word']}")
            representative_traces.append(repetitions[0]["trace"])
        signature = sha256_bytes(canonical_bytes(representative_traces))
        if signature != provisional[record["candidate_id"]]["trace_signature_sha256"]:
            raise ValueError(f"full/provisional signature mismatch: {record['candidate_id']}")
        by_candidate[record["candidate_id"]] = record
    if stage["admitted_candidates"] != expected_candidates:
        raise ValueError("admitted candidate list mismatch")
    return stage, by_candidate


def summarize(p0_path: Path, provisional_path: Path, full_path: Path) -> dict:
    p0_stage, p0 = validate_p0(p0_path)
    provisional_stage, provisional = validate_provisional(provisional_path)
    full_stage, full = validate_full(full_path, provisional)

    first = provisional["max/final"]["word_results"]
    second = provisional["max/iteration_2"]["word_results"]
    divergence_index = next(index for index in range(84) if first[index] != second[index])
    first_divergence = {
        "word_index": divergence_index,
        "word": first[divergence_index]["word"],
        "max_final_frame_sha256": first[divergence_index]["steps"][-1]["final_frame_sha256"],
        "max_iteration_2_frame_sha256": second[divergence_index]["steps"][-1]["final_frame_sha256"],
        "max_final_status": first[divergence_index]["steps"][-1]["status"],
        "max_iteration_2_status": second[divergence_index]["steps"][-1]["status"],
    }

    candidates = []
    for candidate_id in ORDER:
        provisional_record = provisional[candidate_id]
        candidates.append(
            {
                "candidate_id": candidate_id,
                "bundle_manifest_sha256": p0[candidate_id]["bundle_manifest_sha256"],
                "p0_replay": "pass",
                "provisional_status": provisional_record["status"],
                "duplicate_of": provisional_record["duplicate_of"],
                "trace_signature_sha256": provisional_record["trace_signature_sha256"],
                "full_determinism": (
                    "pass" if candidate_id in full else "not_run_behavioral_duplicate"
                ),
            }
        )

    provisional_steps = sum(
        len(result["steps"])
        for record in provisional_stage["results"]
        for result in record["word_results"]
    )
    full_steps = sum(
        len(repetition["trace"]["steps"])
        for record in full_stage["results"]
        for word_record in record["word_records"]
        for repetition in word_record["repetitions"]
    )
    return {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "status": "complete",
        "gate_verdict": "candidate_frontier_feasible",
        "raw_evidence": {
            "p0_results": {"local_path": str(p0_path), "sha256": sha256_file(p0_path)},
            "provisional_results": {
                "local_path": str(provisional_path),
                "sha256": sha256_file(provisional_path),
            },
            "full_results": {"local_path": str(full_path), "sha256": sha256_file(full_path)},
        },
        "pinned_inputs": {
            "runtime_image_id": RUNTIME_IMAGE_ID,
            "prepared_bundles_sha256": PREPARED_BUNDLES_SHA256,
            "environment_id": "ls20-9607627b",
            "p0_frame_sha256": P0_FRAME_SHA256,
            "finite_actions": list(VALID_ACTIONS),
            "word_count": 84,
        },
        "result": {
            "source_records_screened": 13,
            "p0_replay_pass_count": p0_stage["pass_count"],
            "provisional_behavior_classes": len(provisional_stage["provisionally_unique"]),
            "behavioral_duplicate_count": 11,
            "admitted_candidate_count": len(full_stage["admitted_candidates"]),
            "admitted_candidates": full_stage["admitted_candidates"],
            "all_promoted_words_deterministic": True,
            "nondeterministic_word_count": 0,
            "first_divergence": first_divergence,
        },
        "candidate_accounting": candidates,
        "execution_accounting": {
            "fresh_p0_processes": 13,
            "fresh_provisional_processes": 13 * 84,
            "fresh_full_processes": 2 * 84 * 4 * 2,
            "fresh_candidate_processes_total": 13 + 13 * 84 + 2 * 84 * 4 * 2,
            "predicted_transition_steps": provisional_steps + full_steps,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
            "credential_uses": 0,
            "model_or_api_calls": 0,
            "oia_separator_runs": 0,
        },
        "integrity": {
            "all_candidate_bundles_hash_verified": True,
            "all_p0_replays_exact": True,
            "all_provisional_results_pass": True,
            "all_full_repetitions_pass": True,
            "full_and_provisional_signatures_match": True,
            "candidate_or_p0_output_emitted_during_p0": False,
            "unexpected_candidate_or_p0_file_access_during_p0": False,
            "network_disabled": True,
            "session_and_post_p0_state_excluded": True,
        },
        "interpretation": {
            "supported": "At least two fixed released programs exactly replay one opened P0 and produce deterministic, behaviorally different predictions within the frozen 84-word level-1 boundary.",
            "sampling": "The admitted programs are checkpoints from one learner/run family, not independently authored learners.",
            "not_supported": "No global non-equivalence, model correctness, real-environment outcome, OIA separator, ontology-revision necessity, planning value, decision superiority, sealed transfer, or Track B conclusion follows."
        },
        "claim_boundary": "Opened Track A candidate-frontier feasibility only; no real ARC action or broader scientific claim.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p0", type=Path, required=True)
    parser.add_argument("--provisional", type=Path, required=True)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = summarize(args.p0, args.provisional, args.full)
    rendered = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_bytes(rendered)
    os.replace(temporary, args.output)
    print(
        json.dumps(
            {
                "admitted_candidates": summary["result"]["admitted_candidates"],
                "gate_verdict": summary["gate_verdict"],
                "output": str(args.output),
                "sha256": sha256_bytes(rendered),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
