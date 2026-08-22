#!/usr/bin/env python3
"""Envelope-corrected orchestrator for post-P0 Track A 003b admission stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.run_track_a_003b_admission import (
    docker_image_id,
    full_stage,
    load_prepared,
    p0_stage,
    provisional_stage,
    sha256_file,
    write_result,
)


def load_stage_result(path: Path, expected_stage: str) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    stage = document.get("stage_result", document)
    if stage.get("stage") != expected_stage:
        raise ValueError(f"expected {expected_stage!r} stage evidence")
    return stage


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
    prepared_root = args.prepared_root.resolve()
    _, candidates = load_prepared(prepared_root)

    if args.stage == "p0":
        stage = p0_stage(args.image, prepared_root, candidates, args.timeout_seconds)
    elif args.stage == "provisional":
        if args.p0_result is None:
            raise ValueError("--p0-result is required")
        stage = provisional_stage(
            args.image,
            prepared_root,
            candidates,
            load_stage_result(args.p0_result, "p0"),
            args.timeout_seconds,
        )
    else:
        if args.provisional_result is None:
            raise ValueError("--provisional-result is required")
        stage = full_stage(
            args.image,
            prepared_root,
            candidates,
            load_stage_result(args.provisional_result, "provisional"),
            args.timeout_seconds,
        )

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "orchestrator_revision": "v2-envelope-correction",
        "runtime_image_id": observed_image_id,
        "prepared_bundles_sha256": sha256_file(prepared_root / "PREPARED_BUNDLES.json"),
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
