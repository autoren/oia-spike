#!/usr/bin/env python3
"""Run the frozen Track A 003b admission stages in an isolated Docker runtime."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path


VALID_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def frozen_words() -> list[list[str]]:
    return [
        list(word)
        for length in (1, 2, 3)
        for word in itertools.product(VALID_ACTIONS, repeat=length)
    ]


def behavior_projection(result: dict) -> dict:
    return {
        key: result.get(key)
        for key in ("status", "error_category", "p0", "word", "steps")
        if key in result
    }


def docker_image_id(image: str) -> str:
    result = subprocess.run(
        ("docker", "image", "inspect", image, "--format", "{{.Id}}"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def run_once(
    *,
    image: str,
    bundle: Path,
    p0: Path,
    word: list[str],
    seed: int,
    timeout_seconds: int,
) -> dict:
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
        f"type=bind,src={bundle},dst=/candidate,readonly",
        "--mount",
        f"type=bind,src={p0},dst=/p0,readonly",
        image,
        "--word-json",
        json.dumps(word, separators=(",", ":")),
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error_category": "timeout"}
    if completed.returncode != 0:
        return {
            "status": "container_error",
            "error_category": f"container_exit:{completed.returncode}",
            "stderr_bytes": len(completed.stderr),
            "stderr_sha256": sha256_bytes(completed.stderr),
        }
    try:
        result = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "container_error",
            "error_category": "invalid_runner_output",
            "stdout_bytes": len(completed.stdout),
            "stdout_sha256": sha256_bytes(completed.stdout),
        }
    result["container_stderr_bytes"] = len(completed.stderr)
    result["container_stderr_sha256"] = sha256_bytes(completed.stderr)
    return result


def load_prepared(prepared_root: Path) -> tuple[dict, list[tuple[dict, Path]]]:
    manifest = json.loads((prepared_root / "PREPARED_BUNDLES.json").read_text(encoding="utf-8"))
    if manifest["status"] != "candidate_bundles_prepared_behavior_not_run":
        raise ValueError("prepared-bundle status is not pre-outcome")
    candidates: list[tuple[dict, Path]] = []
    for candidate in manifest["candidates"]:
        bundle = prepared_root / "candidates" / candidate["bundle_id"]
        if sha256_file(bundle / "BUNDLE_MANIFEST.json") != candidate["manifest_sha256"]:
            raise ValueError(f"bundle manifest mismatch: {candidate['candidate_id']}")
        for name, record in candidate["files"].items():
            if sha256_file(bundle / name) != record["sha256"]:
                raise ValueError(f"bundle file mismatch: {candidate['candidate_id']}:{name}")
        candidates.append((candidate, bundle))
    return manifest, candidates


def p0_stage(
    image: str,
    prepared_root: Path,
    candidates: list[tuple[dict, Path]],
    timeout_seconds: int,
) -> dict:
    results = []
    for candidate, bundle in candidates:
        observed = run_once(
            image=image,
            bundle=bundle,
            p0=prepared_root / "p0",
            word=[],
            seed=0,
            timeout_seconds=timeout_seconds,
        )
        results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "bundle_manifest_sha256": candidate["manifest_sha256"],
                "result": observed,
                "pass": observed.get("status") == "pass"
                and observed.get("p0", {}).get("matches_frame") is True,
            }
        )
    return {
        "stage": "p0",
        "candidate_count": len(results),
        "pass_count": sum(record["pass"] for record in results),
        "results": results,
    }


def provisional_stage(
    image: str,
    prepared_root: Path,
    candidates: list[tuple[dict, Path]],
    p0_result: dict,
    timeout_seconds: int,
) -> dict:
    p0_pass = {record["candidate_id"] for record in p0_result["results"] if record["pass"]}
    words = frozen_words()
    results = []
    signature_owner: dict[str, str] = {}
    for candidate, bundle in candidates:
        candidate_id = candidate["candidate_id"]
        if candidate_id not in p0_pass:
            results.append({"candidate_id": candidate_id, "status": "not_run_p0_failed"})
            continue
        word_results = []
        for word in words:
            observed = run_once(
                image=image,
                bundle=bundle,
                p0=prepared_root / "p0",
                word=word,
                seed=0,
                timeout_seconds=timeout_seconds,
            )
            word_results.append(behavior_projection(observed))
        signature = sha256_bytes(canonical_bytes(word_results))
        owner = signature_owner.setdefault(signature, candidate_id)
        results.append(
            {
                "candidate_id": candidate_id,
                "status": "provisionally_unique" if owner == candidate_id else "behavioral_duplicate",
                "duplicate_of": None if owner == candidate_id else owner,
                "trace_signature_sha256": signature,
                "word_count": len(word_results),
                "word_results": word_results,
            }
        )
    unique = [record["candidate_id"] for record in results if record["status"] == "provisionally_unique"]
    return {
        "stage": "provisional",
        "seed": 0,
        "word_count": len(words),
        "provisionally_unique": unique,
        "results": results,
    }


def full_stage(
    image: str,
    prepared_root: Path,
    candidates: list[tuple[dict, Path]],
    provisional_result: dict,
    timeout_seconds: int,
) -> dict:
    candidate_map = {candidate["candidate_id"]: (candidate, bundle) for candidate, bundle in candidates}
    words = frozen_words()
    results = []
    for candidate_id in provisional_result["provisionally_unique"][:8]:
        candidate, bundle = candidate_map[candidate_id]
        word_records = []
        deterministic = True
        for word in words:
            repetitions = []
            for seed in (0, 1, 5, 10):
                for repetition in (1, 2):
                    observed = run_once(
                        image=image,
                        bundle=bundle,
                        p0=prepared_root / "p0",
                        word=word,
                        seed=seed,
                        timeout_seconds=timeout_seconds,
                    )
                    repetitions.append(
                        {
                            "seed": seed,
                            "repetition": repetition,
                            "trace": behavior_projection(observed),
                        }
                    )
            hashes = {sha256_bytes(canonical_bytes(record["trace"])) for record in repetitions}
            word_deterministic = len(hashes) == 1
            deterministic = deterministic and word_deterministic
            word_records.append(
                {
                    "word": word,
                    "deterministic": word_deterministic,
                    "trace_sha256": sorted(hashes),
                    "repetitions": repetitions,
                }
            )
        results.append(
            {
                "candidate_id": candidate_id,
                "bundle_manifest_sha256": candidate["manifest_sha256"],
                "deterministic": deterministic,
                "word_count": len(word_records),
                "word_records": word_records,
            }
        )
    admitted = [record["candidate_id"] for record in results if record["deterministic"]]
    return {
        "stage": "full",
        "seeds": [0, 1, 5, 10],
        "repetitions_per_seed": 2,
        "word_count": len(words),
        "admitted_candidates": admitted,
        "results": results,
    }


def write_result(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("p0", "provisional", "full"))
    parser.add_argument("--prepared-root", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--p0-result", type=Path)
    parser.add_argument("--provisional-result", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    observed_image_id = docker_image_id(args.image)
    if observed_image_id != args.expected_image_id:
        raise ValueError("runtime image ID does not match the pre-outcome pin")
    prepared, candidates = load_prepared(args.prepared_root.resolve())
    if args.stage == "p0":
        stage = p0_stage(args.image, args.prepared_root.resolve(), candidates, args.timeout_seconds)
    elif args.stage == "provisional":
        if args.p0_result is None:
            raise ValueError("--p0-result is required")
        p0_result = json.loads(args.p0_result.read_text(encoding="utf-8"))
        stage = provisional_stage(
            args.image,
            args.prepared_root.resolve(),
            candidates,
            p0_result,
            args.timeout_seconds,
        )
    else:
        if args.provisional_result is None:
            raise ValueError("--provisional-result is required")
        provisional_result = json.loads(args.provisional_result.read_text(encoding="utf-8"))
        stage = full_stage(
            args.image,
            args.prepared_root.resolve(),
            candidates,
            provisional_result,
            args.timeout_seconds,
        )
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "runtime_image_id": observed_image_id,
        "prepared_bundles_sha256": sha256_file(
            args.prepared_root.resolve() / "PREPARED_BUNDLES.json"
        ),
        "isolation": {
            "network": "none",
            "root_filesystem": "read_only",
            "candidate_mount": "read_only",
            "p0_mount": "read_only",
            "capabilities": "all_dropped",
            "no_new_privileges": True,
            "unprivileged_uid_gid": "65532:65532",
            "bounded_resources": True,
        },
        "stage_result": stage,
        "claim_boundary": "Opened Track A candidate admission only; no ARC, OIA separator, sealed, ontology-revision, decision-value, or Track B claim.",
    }
    write_result(args.output, result)
    print(json.dumps({"output": str(args.output), "stage": args.stage}, sort_keys=True))


if __name__ == "__main__":
    main()
