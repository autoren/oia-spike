#!/usr/bin/env python3
"""Run the frozen Track A 004a retrospective audit with accepted OIA v0.2.1."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-004a"
OUTCOME_ROOT = AUDIT_ROOT / "outcome"
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
INPUT_PATH = AUDIT_ROOT / "OIA_INPUT.frozen.json"
SOURCE_PATH = AUDIT_ROOT / "ADAPTER_SOURCE_TRACES.json"
OUTPUTS_PATH = AUDIT_ROOT / "OUTPUT_MANIFEST.opened.json"
SEEDS = (0, 1, 5, 10)
OUTCOME_FILES = (
    "EXECUTION_RECORD.json",
    "OIA_REPORT.json",
    "POLICY_REPLAY.json",
    "RETROSPECTIVE_RESULT.md",
    "SHA256SUMS.txt",
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_checksums(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        target = ROOT / relative
        if not target.is_file() or target.is_symlink() or sha256_file(target) != digest:
            raise RuntimeError(f"checksum mismatch: {relative}")
        count += 1
    return count


def run_oia_subprocess(seed: int) -> bytes:
    command = (
        sys.executable,
        "-m",
        "ontology_auditor.cli",
        str(INPUT_PATH),
    )
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = str(seed)
    environment["PYTHONPATH"] = str(BASELINE_SRC)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.stderr:
        raise RuntimeError(f"OIA emitted stderr under seed {seed}")
    return completed.stdout


def observation_id(observation: Mapping[str, object]) -> str:
    return "OBS_" + sha256_bytes(canonical_bytes(observation))


def observation_projection(step: Mapping[str, object]) -> dict[str, object]:
    return {
        key: step[key]
        for key in (
            "status",
            "error_category",
            "final_frame_sha256",
            "modeled_progress",
        )
        if key in step
    }


def candidate_observations(source: Mapping[str, object]) -> dict[str, dict[tuple[str, ...], tuple[str, ...]]]:
    result: dict[str, dict[tuple[str, ...], tuple[str, ...]]] = {}
    for candidate in source["candidates"]:
        machine_id = str(candidate["machine_id"])
        by_word: dict[tuple[str, ...], tuple[str, ...]] = {}
        for record in candidate["word_records"]:
            word = tuple(record["word"])
            by_word[word] = tuple(
                observation_id(observation_projection(step))
                for step in record["trace"]["steps"]
            )
        result[machine_id] = by_word
    return result


def independent_first_separator(
    source: Mapping[str, object],
) -> tuple[str, ...] | None:
    by_candidate = candidate_observations(source)
    left, right = sorted(by_candidate)
    words = [tuple(record["word"]) for record in source["candidates"][0]["word_records"]]
    for word in words:
        if by_candidate[left][word] != by_candidate[right][word]:
            return word
    return None


def replay_policy(
    source: Mapping[str, object],
    policy: Mapping[str, object],
) -> dict[str, object]:
    by_candidate = candidate_observations(source)
    rows: list[dict[str, object]] = []
    for machine_id in sorted(by_candidate):
        node = policy
        word: tuple[str, ...] = ()
        trace: list[dict[str, str]] = []
        while node.get("type") == "action":
            action = str(node["action"])
            word = word + (action,)
            if word not in by_candidate[machine_id]:
                raise AssertionError("policy left the frozen source trace envelope")
            output = by_candidate[machine_id][word][-1]
            trace.append({"action": action, "output": output})
            branches = node.get("branches")
            if not isinstance(branches, Mapping) or output not in branches:
                raise AssertionError("policy has no branch for source observation")
            child = branches[output]
            if not isinstance(child, Mapping):
                raise TypeError("policy child must be an object")
            node = child
        candidates = node.get("candidates")
        if not isinstance(candidates, list) or machine_id not in candidates:
            raise AssertionError("policy leaf excludes the replayed candidate")
        rows.append(
            {
                "machine_id": machine_id,
                "leaf_candidates": candidates,
                "steps": len(trace),
                "trace": trace,
                "result": "pass",
            }
        )
    return {
        "audit_id": "OIA-1-TRACK-A-004a",
        "baseline": "direct lookup in frozen Track A 003b source traces",
        "uses_compiled_machine_transitions": False,
        "selection_role": "none; retrospective policy verification only",
        "all_paths_valid": True,
        "maximum_steps": max(row["steps"] for row in rows),
        "rows": rows,
    }


def result_markdown(execution: Mapping[str, object]) -> str:
    sequence = " → ".join(execution["minimum_separator"])
    return f"""# OIA-1 Track A 004a retrospective result

The gate passed. Unchanged accepted OIA-1 v0.2.1 returned an exact, globally
minimum one-step identification policy for the two Track A 003b predictive
programs. Its selected intervention was `{sequence}`. Independent lookup in the
frozen source traces verified both branches and the one-step worst-case depth.

This is a **retrospective external instrument-validation result**. The complete
source traces—and therefore their first divergence—were known before the
adapter and OIA input were frozen. The result shows that the frozen OIA can
reconstruct and certify that separator without tuning its accepted core; it is
not evidence that OIA prospectively discovered an unknown separator.

No candidate program or ARC environment was executed in this gate. It made no
real ARC action, model/API call, credential use, network/service call, private or
sealed evaluation, ontology-revision claim, planning-superiority claim, or
Track B claim.
"""


def write_json(path: Path, value: object) -> None:
    path.write_bytes(pretty_bytes(value))


def main() -> None:
    if OUTCOME_ROOT.exists():
        raise RuntimeError("Track A 004a outcome already exists; refusing to overwrite")
    pre_run_count = verify_checksums(AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt")

    rendered_by_seed = {seed: run_oia_subprocess(seed) for seed in SEEDS}
    hashes = {seed: sha256_bytes(rendered) for seed, rendered in rendered_by_seed.items()}
    if len(set(rendered_by_seed.values())) != 1:
        raise RuntimeError("OIA report serialization differs across PYTHONHASHSEED")
    primary_bytes = rendered_by_seed[SEEDS[0]]
    report = json.loads(primary_bytes)

    sys.path.insert(0, str(BASELINE_SRC))
    from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    system = CandidateSystem.from_dict(payload)
    adaptive = report["full_candidate_identification"]["adaptive"]
    if not isinstance(adaptive, Mapping):
        raise TypeError("adaptive result must be an object")
    verified_depth = verify_serialized_adaptive_result(system, adaptive)
    if adaptive.get("status") != "solved":
        raise RuntimeError("OIA did not solve candidate identification")
    if adaptive.get("exact") is not True or adaptive.get("optimality_certified") is not True:
        raise RuntimeError("OIA result lacks exact optimality certification")
    policy = adaptive.get("policy")
    if not isinstance(policy, Mapping):
        raise RuntimeError("OIA result lacks an executable policy")

    separator = independent_first_separator(source)
    pairwise = report["pairwise_separation"]
    if separator is None or len(pairwise) != 1 or pairwise[0]["sequence"] != list(separator):
        raise RuntimeError("OIA pairwise result disagrees with frozen source traces")
    replay = replay_policy(source, policy)
    if verified_depth != replay["maximum_steps"]:
        raise RuntimeError("serialized witness depth disagrees with source replay")

    execution = {
        "audit_id": "OIA-1-TRACK-A-004a",
        "schema_version": 1,
        "status": "complete",
        "gate_verdict": "retrospective_instrument_validation_pass",
        "classification": "retrospective_external_instrument_validation",
        "accepted_engine": "OIA-1 v0.2.1",
        "freeze_manifest_verified_entries": pre_run_count,
        "oia_input_sha256": sha256_file(INPUT_PATH),
        "oia_report_sha256": sha256_bytes(primary_bytes),
        "cross_process_serialization": {
            "pythonhashseed_values": list(SEEDS),
            "exact_bytes_equal": True,
            "report_sha256_by_seed": {str(seed): digest for seed, digest in hashes.items()},
        },
        "primary_endpoint": "full_candidate_identification.adaptive",
        "adaptive_status": adaptive["status"],
        "exact": adaptive["exact"],
        "enumeration_complete": adaptive["enumeration_complete"],
        "optimality_certified": adaptive["optimality_certified"],
        "depth_claim": adaptive["depth_claim"],
        "verified_worst_case_steps": verified_depth,
        "minimum_separator": list(separator),
        "policy_source_trace_replay_all_paths_valid": replay["all_paths_valid"],
        "execution_accounting": {
            "oia_processes": len(SEEDS),
            "candidate_processes": 0,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
            "credential_uses": 0,
            "model_or_api_calls": 0,
            "private_or_sealed_evaluations": 0,
        },
        "claim_boundary": (
            "Retrospective opened Track A instrument validation only; complete "
            "candidate traces were known before freeze, so prospective discovery, "
            "real-outcome, decision-value, sealed-transfer, and Track B claims are excluded."
        ),
    }

    OUTCOME_ROOT.mkdir(parents=False)
    (OUTCOME_ROOT / "OIA_REPORT.json").write_bytes(primary_bytes)
    write_json(OUTCOME_ROOT / "POLICY_REPLAY.json", replay)
    write_json(OUTCOME_ROOT / "EXECUTION_RECORD.json", execution)
    (OUTCOME_ROOT / "RETROSPECTIVE_RESULT.md").write_text(
        result_markdown(execution), encoding="utf-8"
    )
    checksum_names = (
        "EXECUTION_RECORD.json",
        "OIA_REPORT.json",
        "POLICY_REPLAY.json",
        "RETROSPECTIVE_RESULT.md",
    )
    (OUTCOME_ROOT / "SHA256SUMS.txt").write_text(
        "\n".join(
            f"{sha256_file(OUTCOME_ROOT / name)}  {name}" for name in checksum_names
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "audit_id": "OIA-1-TRACK-A-004a",
        "gate_verdict": execution["gate_verdict"],
        "files": [
            {
                "path": name,
                "sha256": sha256_file(OUTCOME_ROOT / name),
                "size_bytes": (OUTCOME_ROOT / name).stat().st_size,
            }
            for name in OUTCOME_FILES
        ],
        "pre_run_manifest_sha256": sha256_file(AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt"),
    }
    write_json(OUTCOME_ROOT / "PACKAGE_MANIFEST.json", manifest)
    print(json.dumps(execution, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
