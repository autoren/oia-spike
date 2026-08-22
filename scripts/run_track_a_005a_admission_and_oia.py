#!/usr/bin/env python3
"""Run frozen Track A 005a admission and select an OIA separator pre-outcome."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SRC = ROOT / "baseline" / "oia-v0.2.1" / "src"
ACTIONS = ("ACTION6", "ACTION7")
HORIZON = 3
SEEDS = (0, 1, 5, 10)
REPETITIONS = (1, 2)
EXPECTED_CANDIDATES = ("C0006", "C0008")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
BOUNDARY_OUTPUT = "OBS_BOUNDARY_EXHAUSTED"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def frozen_words() -> list[tuple[str, ...]]:
    return [
        word
        for length in range(1, HORIZON + 1)
        for word in itertools.product(ACTIONS, repeat=length)
    ]


def behavior_projection(result: Mapping[str, object]) -> dict[str, object]:
    return {
        key: result[key]
        for key in ("status", "error_category", "p0", "word", "steps")
        if key in result
    }


def observation_projection(step: Mapping[str, object]) -> dict[str, object]:
    return {
        "final_frame_sha256": step["final_frame_sha256"],
        "status": step["status"],
    }


def observation_id(step: Mapping[str, object]) -> str:
    return "OBS_" + sha256_bytes(canonical_bytes(observation_projection(step)))


def valid_pass(result: Mapping[str, object], word: tuple[str, ...]) -> bool:
    emissions = result.get("emissions", {})
    accesses = result.get("file_accesses", [])
    return (
        result.get("status") == "pass"
        and result.get("error_category") is None
        and result.get("word") == list(word)
        and isinstance(result.get("steps"), list)
        and len(result["steps"]) == len(word)
        and result.get("p0", {}).get("matches_frame") is True
        and emissions.get("stdout_bytes") == 0
        and emissions.get("stderr_bytes") == 0
        and emissions.get("stdout_sha256") == EMPTY_SHA256
        and emissions.get("stderr_sha256") == EMPTY_SHA256
        and set(accesses) <= {"candidate/candidate.py", "p0/initial_frame.txt"}
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
    p0: Path,
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
        f"type=bind,src={p0},dst=/p0,readonly",
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
    if manifest["status"] != "candidate_bundles_prepared_behavior_not_run":
        raise ValueError("candidate preparation did not produce a frontier")
    candidates = [
        row
        for row in manifest["candidate_records"]
        if row["status"] == "prepared_not_imported_or_executed"
    ]
    if tuple(row["candidate_id"] for row in candidates) != EXPECTED_CANDIDATES:
        raise ValueError("prepared candidate identity changed")
    for row in candidates:
        path = root / "candidates" / row["candidate_id"] / "candidate.py"
        if sha256_file(path) != row["candidate_sha256"]:
            raise ValueError(f"prepared candidate hash changed: {row['candidate_id']}")
    return manifest, candidates


def p0_stage(
    image: str,
    prepared_root: Path,
    candidates: Sequence[Mapping[str, object]],
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
    records = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        observed = run_once(
            image=image,
            candidate=prepared_root / "candidates" / candidate_id,
            p0=prepared_root / "p0",
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
    return {"stage": "p0", "records": records}


def provisional_stage(
    image: str,
    prepared_root: Path,
    candidates: Sequence[Mapping[str, object]],
    p0: Mapping[str, object],
    timeout_seconds: int,
    accounting: dict[str, int],
) -> dict[str, object]:
    p0_pass = {row["candidate_id"] for row in p0["records"] if row["pass"]}
    signature_owner: dict[str, str] = {}
    records = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in p0_pass:
            records.append({"candidate_id": candidate_id, "status": "not_run_p0_failed"})
            continue
        word_records = []
        all_pass = True
        for word in frozen_words():
            observed = run_once(
                image=image,
                candidate=prepared_root / "candidates" / candidate_id,
                p0=prepared_root / "p0",
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
        "stage": "provisional",
        "seed": 0,
        "word_count": len(frozen_words()),
        "records": records,
        "provisionally_unique": [
            row["candidate_id"] for row in records if row["status"] == "provisionally_unique"
        ],
    }


def full_stage(
    image: str,
    prepared_root: Path,
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
                        candidate=prepared_root / "candidates" / candidate_id,
                        p0=prepared_root / "p0",
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
        "stage": "full",
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


def canonical_traces(full: Mapping[str, object]) -> dict[str, dict[tuple[str, ...], Mapping[str, object]]]:
    result = {}
    for candidate in full["records"]:
        if candidate["candidate_id"] not in full["admitted_candidates"]:
            continue
        by_word = {}
        for record in candidate["word_records"]:
            traces = [row["trace"] for row in record["repetitions"]]
            if any(trace != traces[0] for trace in traces[1:]):
                raise ValueError("full-stage trace disagreement")
            by_word[tuple(record["word"])] = traces[0]
        result[candidate["candidate_id"]] = by_word
    return result


def build_adapter(full: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    traces = canonical_traces(full)
    prefixes = [()] + frozen_words()
    state_by_prefix = {prefix: f"S{index:03d}" for index, prefix in enumerate(prefixes)}
    sink = f"S{len(prefixes):03d}"
    outputs: dict[str, object] = {
        BOUNDARY_OUTPUT: {"kind": "candidate_independent_depth_boundary"}
    }
    machines = []
    validation = []
    for index, candidate_id in enumerate(full["admitted_candidates"], start=1):
        by_word = traces[candidate_id]
        step_by_prefix: dict[tuple[str, ...], Mapping[str, object]] = {}
        for word, trace in by_word.items():
            for depth, step in enumerate(trace["steps"], start=1):
                prefix = word[:depth]
                previous = step_by_prefix.setdefault(prefix, step)
                if observation_projection(previous) != observation_projection(step):
                    raise ValueError(f"prefix inconsistency: {candidate_id}/{prefix}")
        if set(step_by_prefix) != set(frozen_words()):
            raise ValueError(f"incomplete prefix coverage: {candidate_id}")
        transitions = {}
        for prefix, state in state_by_prefix.items():
            transitions[state] = {}
            for action in ACTIONS:
                if len(prefix) < HORIZON:
                    successor = prefix + (action,)
                    step = step_by_prefix[successor]
                    output = observation_id(step)
                    observation = observation_projection(step)
                    if output in outputs and outputs[output] != observation:
                        raise RuntimeError("observation hash collision")
                    outputs[output] = observation
                    next_state = state_by_prefix[successor]
                else:
                    output = BOUNDARY_OUTPUT
                    next_state = sink
                transitions[state][action] = {"next_state": next_state, "output": output}
        transitions[sink] = {
            action: {"next_state": sink, "output": BOUNDARY_OUTPUT}
            for action in ACTIONS
        }
        machine_id = f"M{index:04d}"
        machines.append(
            {
                "name": machine_id,
                "initial_state": state_by_prefix[()],
                "metadata": {
                    "adapter": "bounded_prefix_tree_v1",
                    "candidate_id_sha256": sha256_bytes(candidate_id.encode("utf-8")),
                },
                "transitions": transitions,
            }
        )
        validation.append(
            {"candidate_id": candidate_id, "machine_id": machine_id, "result": "pass"}
        )
    payload = {
        "machines": machines,
        "options": {
            "max_beliefs": 100_000,
            "max_partitions": 100_000,
            "max_task_loss_frontier": 50_000,
            "value_depth": HORIZON,
        },
    }
    return payload, {
        "adapter": "bounded_prefix_tree_v1",
        "actions": list(ACTIONS),
        "horizon": HORIZON,
        "candidate_checks": validation,
        "output_manifest": outputs,
        "observation_fields": ["final_frame_sha256", "status"],
        "result": "pass",
    }


def run_oia(payload_path: Path, accounting: dict[str, int]) -> tuple[bytes, dict[str, str]]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(BASELINE_SRC)
    rendered = {}
    for seed in SEEDS:
        environment["PYTHONHASHSEED"] = str(seed)
        completed = subprocess.run(
            (sys.executable, "-m", "ontology_auditor.cli", str(payload_path)),
            cwd=ROOT,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        accounting["oia_processes"] += 1
        if completed.stderr:
            raise RuntimeError(f"OIA emitted stderr under seed {seed}")
        rendered[seed] = completed.stdout
    if len(set(rendered.values())) != 1:
        raise RuntimeError("OIA serialization differs across PYTHONHASHSEED")
    return rendered[SEEDS[0]], {
        str(seed): sha256_bytes(value) for seed, value in rendered.items()
    }


def independent_separator(full: Mapping[str, object]) -> tuple[str, ...] | None:
    traces = canonical_traces(full)
    if len(traces) != 2:
        return None
    left, right = traces.values()
    for word in frozen_words():
        left_outputs = [observation_id(step) for step in left[word]["steps"]]
        right_outputs = [observation_id(step) for step in right[word]["steps"]]
        if left_outputs != right_outputs:
            return word
    return None


def blocker_verdict(p0: Mapping[str, object], provisional: Mapping[str, object], full: Mapping[str, object]) -> str:
    if any(not row["pass"] for row in p0["records"]):
        return "replay_failure"
    if len(provisional["provisionally_unique"]) < 2:
        return "no_behavioral_divergence"
    if len(full["admitted_candidates"]) < 2:
        return "nondeterministic_or_runtime_blocker"
    return "candidate_frontier_feasible"


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
    prepared, candidates = load_prepared(prepared_root)
    output_root.mkdir(parents=True)
    accounting = {
        "candidate_processes": 0,
        "oia_processes": 0,
        "real_arc_actions": 0,
        "held_out_post_p0_payloads_read": 0,
        "network_or_service_calls": 0,
        "model_or_api_calls": 0,
        "credential_uses": 0,
        "private_or_sealed_evaluations": 0,
    }
    p0 = p0_stage(args.image, prepared_root, candidates, args.timeout_seconds, accounting)
    provisional = provisional_stage(
        args.image, prepared_root, candidates, p0, args.timeout_seconds, accounting
    )
    full = full_stage(
        args.image,
        prepared_root,
        candidates,
        provisional,
        args.timeout_seconds,
        accounting,
    )
    verdict = blocker_verdict(p0, provisional, full)
    adapter_validation = None
    separator = None
    oia_hashes = None
    oia_report_sha256 = None
    if verdict == "candidate_frontier_feasible":
        payload, adapter_validation = build_adapter(full)
        payload_path = output_root / "OIA_INPUT.json"
        payload_path.write_bytes(pretty_bytes(payload))
        report_bytes, oia_hashes = run_oia(payload_path, accounting)
        report = json.loads(report_bytes)
        sys.path.insert(0, str(BASELINE_SRC))
        from ontology_auditor import CandidateSystem, verify_serialized_adaptive_result

        system = CandidateSystem.from_dict(payload)
        adaptive = report["full_candidate_identification"]["adaptive"]
        depth = verify_serialized_adaptive_result(system, adaptive)
        separator = independent_separator(full)
        pairwise = report["pairwise_separation"]
        if (
            separator is None
            or adaptive["status"] != "solved"
            or adaptive["exact"] is not True
            or adaptive["optimality_certified"] is not True
            or len(pairwise) != 1
            or pairwise[0]["sequence"] != list(separator)
            or depth != len(separator)
        ):
            raise RuntimeError("OIA exact separator checks failed")
        verdict = "prospective_separator_selected_pre_outcome"
        (output_root / "OIA_REPORT.json").write_bytes(report_bytes)
        (output_root / "ADAPTER_VALIDATION.json").write_bytes(
            pretty_bytes(adapter_validation)
        )
        oia_report_sha256 = sha256_bytes(report_bytes)

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "gate_verdict": verdict,
        "runtime_image_id": image_id,
        "prepared_bundles_sha256": sha256_file(
            prepared_root / "PREPARED_BUNDLES.json"
        ),
        "stages": {"p0": p0, "provisional": provisional, "full": full},
        "adapter_validation": adapter_validation,
        "minimum_separator": list(separator) if separator is not None else None,
        "oia_report_sha256": oia_report_sha256,
        "cross_process_oia_report_sha256": oia_hashes,
        "execution_accounting": accounting,
        "epistemic_ordering": {
            "candidate_generation_frozen_before_inference": True,
            "candidate_package_merged_before_source_open": True,
            "runner_adapter_and_oia_path_merged_before_candidate_source_open": True,
            "oia_separator_selected_before_held_out_post_p0_outcome": True,
            "held_out_post_p0_payloads_read": 0,
        },
        "claim_boundary": (
            "Opened Track A candidate admission and exact OIA separator selection "
            "before held-out post-P0 outcome access. No real ARC action, outcome "
            "agreement, decision-value, sealed-transfer, or Track B claim."
        ),
    }
    (output_root / "ADMISSION_AND_OIA_RESULT.json").write_bytes(pretty_bytes(result))
    print(
        json.dumps(
            {
                "admitted": len(full["admitted_candidates"]),
                "candidate_processes": accounting["candidate_processes"],
                "gate_verdict": verdict,
                "minimum_separator": result["minimum_separator"],
                "oia_processes": accounting["oia_processes"],
                "result_sha256": sha256_file(
                    output_root / "ADMISSION_AND_OIA_RESULT.json"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
