#!/usr/bin/env python3
"""Verify the complete Track A 005b pre-inference revision freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005b"
SOURCE_EVIDENCE = (
    ROOT
    / "audits"
    / "track-a-005a"
    / "archive-outcome"
    / "ARCHIVE_OUTCOME_EVIDENCE.zip"
)
EXPECTED_SOURCE_SHA256 = "e6de7cd8db997c561cfb4be078cc3437347af90f9c59e402761c7d790e3ed3a4"
EXPECTED_MODEL_REVISION = "3e6447f082e89cc7f0bc6e5441afd38dfce760ff"
EXPECTED_IMAGE_ID = "sha256:32272ac8ae641808d6b6328bcdb7210746292ea12e4aeea8b69ef93cab49ee2b"
EXPECTED_PATHS = {
    "audits/track-a-005b/PRE_REVISION_EXECUTION_RUNTIME.json",
    "audits/track-a-005b/README.md",
    "audits/track-a-005b/REVISION_BEHAVIOR_AND_OIA_PROTOCOL.frozen.json",
    "audits/track-a-005b/REVISION_GENERATION_PROMPT.template.txt",
    "audits/track-a-005b/REVISION_GENERATION_PROTOCOL.frozen.json",
    "audits/track-a-005b/REVISION_HYPOTHESIS_STANCES.frozen.json",
    "audits/track-a-005b/revision-input/REVISION_INPUT_MANIFEST.json",
    "audits/track-a-005b/revision-input/V1/intermediate_00.txt",
    "audits/track-a-005b/revision-input/V1/intermediate_01.txt",
    "audits/track-a-005b/revision-input/V1/intermediate_02.txt",
    "audits/track-a-005b/revision-input/V1/intermediate_03.txt",
    "audits/track-a-005b/revision-input/V2/intermediate_00.txt",
    "audits/track-a-005b/revision-input/V2/intermediate_01.txt",
    "audits/track-a-005b/revision-input/V2/intermediate_02.txt",
    "audits/track-a-005b/revision-input/V2/intermediate_03.txt",
    "audits/track-a-005b/revision-input/p0.txt",
    "audits/track-a-005b/revision-input/p1_settled.txt",
    "runtime/track-a-005b/Dockerfile",
    "runtime/track-a-005b/candidate_runner.py",
    "scripts/extract_track_a_005b_revision_input.py",
    "scripts/generate_track_a_005b_candidates.py",
    "scripts/prepare_track_a_005b_admission.py",
    "scripts/run_track_a_005b_admission_and_oia.py",
    "scripts/verify_track_a_005b_behavior_outcome.py",
    "scripts/verify_track_a_005b_generation_result.py",
    "scripts/verify_track_a_005b_revision_freeze.py",
    "tests/fixtures/track-a-005b/synthetic_candidate/candidate.py",
    "tests/test_track_a_005b_admission.py",
    "tests/test_track_a_005b_revision_generation.py",
}

sys.path.insert(0, str(ROOT / "scripts"))
import generate_track_a_005b_candidates as generation


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    observed_paths: set[str] = set()
    checksum_path = AUDIT_ROOT / "REVISION_FREEZE_SHA256SUMS.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError(f"005b revision-freeze checksum mismatch: {relative}")
        if relative in observed_paths:
            raise ValueError(f"duplicate 005b revision-freeze path: {relative}")
        observed_paths.add(relative)
    if observed_paths != EXPECTED_PATHS:
        raise ValueError("005b revision-freeze path set changed")
    if sha256(SOURCE_EVIDENCE) != EXPECTED_SOURCE_SHA256:
        raise ValueError("opened step-1 source evidence changed")

    input_manifest = load(AUDIT_ROOT / "revision-input" / "REVISION_INPUT_MANIFEST.json")
    if input_manifest["source"] != {
        "later_step_payloads_read": 0,
        "opened_step1_evidence_sha256": EXPECTED_SOURCE_SHA256,
        "record_count": 5,
    }:
        raise ValueError("005b revision source boundary changed")
    if input_manifest["p1_settled"]["replicate_count"] != 5:
        raise ValueError("005b settled replication changed")
    if sorted(row["multiplicity"] for row in input_manifest["transient_variants"]) != [2, 3]:
        raise ValueError("005b transient variant accounting changed")
    for record in (input_manifest["p0"], input_manifest["p1_settled"]):
        if sha256(AUDIT_ROOT / "revision-input" / record["path"]) != record["sha256"]:
            raise ValueError(f"005b revision raster changed: {record['path']}")
    for variant in input_manifest["transient_variants"]:
        if len(variant["frames"]) != 4:
            raise ValueError("005b transient frame count changed")
        for frame in variant["frames"]:
            if sha256(AUDIT_ROOT / "revision-input" / frame["path"]) != frame["sha256"]:
                raise ValueError(f"005b transient frame changed: {frame['path']}")

    provenance = load(ROOT / "audits" / "track-a-005a" / "GENERATION_RUNTIME_PROVENANCE.json")
    if provenance["model"]["revision"] != EXPECTED_MODEL_REVISION:
        raise ValueError("005b local model revision changed")
    generation_protocol = load(AUDIT_ROOT / "REVISION_GENERATION_PROTOCOL.frozen.json")
    if generation_protocol["status_at_freeze"] != "frozen_before_any_revision_generation_inference":
        raise ValueError("005b generation ordering changed")
    if generation_protocol["sampling"] != {
        "decode": "greedy",
        "enable_thinking": False,
        "maximum_output_tokens_per_candidate": 2200,
        "prompt_count": 8,
        "prompt_order": [f"R{index:04d}" for index in range(1, 9)],
        "temperature": 0.0,
    }:
        raise ValueError("005b generation sampling changed")
    if generation_protocol["parser"]["repair_inferences"] != 0:
        raise ValueError("005b repair boundary changed")
    if generation_protocol["input_boundary"]["later_step_payloads_read"] != 0:
        raise ValueError("005b later-step input boundary crossed")

    stances = load(AUDIT_ROOT / "REVISION_HYPOTHESIS_STANCES.frozen.json")["stances"]
    if [row["candidate_id"] for row in stances] != [f"R{index:04d}" for index in range(1, 9)]:
        raise ValueError("005b stance order changed")
    if len({row["stance_id"] for row in stances}) != 8:
        raise ValueError("005b stances are not unique")
    template = (AUDIT_ROOT / "REVISION_GENERATION_PROMPT.template.txt").read_text(
        encoding="utf-8"
    )
    for stance in stances:
        prompt = generation.render_prompt(template, stance, input_manifest)
        for forbidden in ("su15", "article2_main_runs_additional", "step_0002"):
            if forbidden in prompt:
                raise ValueError(f"forbidden 005b prompt token: {forbidden}")

    behavior = load(AUDIT_ROOT / "REVISION_BEHAVIOR_AND_OIA_PROTOCOL.frozen.json")
    if behavior["status_at_freeze"] != "frozen_before_revision_generation_inference_or_candidate_execution":
        raise ValueError("005b behavior ordering changed")
    if behavior["action_language"]["word_count"] != 14:
        raise ValueError("005b post-P1 language changed")
    if behavior["adapter_and_oia"]["observation_fields"] != [
        "final_frame_sha256",
        "status",
    ]:
        raise ValueError("005b observation boundary changed")
    if behavior["epistemic_ordering"]["step_2_or_later_payloads_read"] != 0:
        raise ValueError("005b step-2 boundary changed")

    runtime = load(AUDIT_ROOT / "PRE_REVISION_EXECUTION_RUNTIME.json")
    if runtime["runtime"]["image_id"] != EXPECTED_IMAGE_ID:
        raise ValueError("005b runtime image changed")
    if runtime["synthetic_smoke_test"]["status"] != "pass":
        raise ValueError("005b synthetic smoke test changed")
    for record in runtime["source_pins"]:
        path = ROOT / record["path"]
        if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"005b runtime source pin changed: {record['path']}")
    if any(runtime["execution_boundary"].values()):
        raise ValueError("005b pre-inference execution boundary crossed")

    print(
        json.dumps(
            {
                "audit_id": "OIA-1-TRACK-A-005b",
                "image_id": EXPECTED_IMAGE_ID,
                "manifest_entries": len(observed_paths),
                "pass": True,
                "status": "revision_generation_behavior_and_oia_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
