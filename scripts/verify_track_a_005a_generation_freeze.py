#!/usr/bin/env python3
"""Verify the Track A 005a local candidate-generation freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
EXPECTED_P0 = {
    "initial_frame.png": "a4866d89296b2191b5f7e056bc61715ff0c340394392bcbb15ceb95c8dd91953",
    "initial_frame.txt": "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6",
    "initial_metadata.json": "3d9543812b624974d09b72111b55c0f99802220ed919ce79aa21b4d5e39a8281",
}
EXPECTED_MANIFEST_PATHS = {
    "audits/track-a-005a/CANDIDATE_GENERATION_PROTOCOL.frozen.json",
    "audits/track-a-005a/GENERATION_PROMPT.template.txt",
    "audits/track-a-005a/GENERATION_RUNTIME_INVENTORY_ERRATUM.pre-inference.json",
    "audits/track-a-005a/GENERATION_RUNTIME_PROVENANCE.json",
    "audits/track-a-005a/GENERATION_RUNTIME_REQUIREMENTS.lock.txt",
    "audits/track-a-005a/HYPOTHESIS_STANCES.frozen.json",
    "scripts/generate_track_a_005a_candidates.py",
    "scripts/inventory_track_a_005a_generation_runtime.py",
    "scripts/verify_track_a_005a_generation_freeze.py",
    "scripts/verify_track_a_005a_generation_result.py",
    "tests/test_track_a_005a_candidate_generation.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> object:
    return json.loads((AUDIT_ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    observed_paths: set[str] = set()
    for line in (AUDIT_ROOT / "GENERATION_FREEZE_SHA256SUMS.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"generation-freeze checksum mismatch: {relative}")
        if relative in observed_paths:
            raise ValueError(f"duplicate generation-freeze manifest path: {relative}")
        observed_paths.add(relative)
    if observed_paths != EXPECTED_MANIFEST_PATHS:
        raise ValueError("generation-freeze manifest path set changed")

    provenance = load("GENERATION_RUNTIME_PROVENANCE.json")
    model = provenance["model"]
    if model["repository"] != "mlx-community/Qwen3.8-27B-4bit":
        raise ValueError("local generation model changed")
    if model["revision"] != "3e6447f082e89cc7f0bc6e5441afd38dfce760ff":
        raise ValueError("local model revision changed")
    if model["license"] != "Apache-2.0" or model["file_count"] != 13:
        raise ValueError("model provenance changed")
    if model["total_size_bytes"] != sum(row["size_bytes"] for row in model["files"]):
        raise ValueError("model size accounting changed")
    if len({row["path"] for row in model["files"]}) != 13:
        raise ValueError("model file accounting is not unique")
    if provenance["access_accounting"]["inference_tokens_generated"] != 0:
        raise ValueError("inference occurred before generation freeze")

    requirements = {}
    for line in (AUDIT_ROOT / "GENERATION_RUNTIME_REQUIREMENTS.lock.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        name, version = line.split("==", 1)
        requirements[name] = version
    for name, version in provenance["runtime"]["packages"].items():
        if requirements.get(name) != version:
            raise ValueError(f"runtime lock mismatch: {name}")

    for name, digest in EXPECTED_P0.items():
        if sha256(AUDIT_ROOT / "p0" / name) != digest:
            raise ValueError(f"generation P0 changed: {name}")
    stances = load("HYPOTHESIS_STANCES.frozen.json")
    rows = stances["stances"]
    if len(rows) != 8:
        raise ValueError("hypothesis stance count changed")
    if [row["candidate_id"] for row in rows] != [f"C{index:04d}" for index in range(1, 9)]:
        raise ValueError("candidate order changed")
    if len({row["stance_id"] for row in rows}) != 8:
        raise ValueError("hypothesis stances are not unique")
    prompt = (AUDIT_ROOT / "GENERATION_PROMPT.template.txt").read_text(encoding="utf-8")
    for placeholder in (
        "{{STANCE_ID}}",
        "{{STANCE_INSTRUCTION}}",
        "{{CANDIDATE_ID}}",
        "{{ACTION_NAMES}}",
        "{{P0_FRAME}}",
    ):
        if placeholder not in prompt:
            raise ValueError(f"generation prompt placeholder missing: {placeholder}")

    protocol = load("CANDIDATE_GENERATION_PROTOCOL.frozen.json")
    if protocol["status_at_freeze"] != "frozen_before_any_candidate_generation_inference":
        raise ValueError("candidate generation ordering changed")
    if protocol["sampling"]["temperature"] != 0.0 or protocol["sampling"]["decode"] != "greedy":
        raise ValueError("generation sampling changed")
    if protocol["repairs"]["maximum_repair_inferences"] != 0:
        raise ValueError("candidate repair boundary changed")
    if protocol["future_execution"]["generated_candidates_may_execute_during_this_gate"] is not False:
        raise ValueError("candidate execution boundary changed")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005a",
                "manifest_entries": len(observed_paths),
                "model_revision": model["revision"],
                "pass": True,
                "status": "candidate_generation_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
