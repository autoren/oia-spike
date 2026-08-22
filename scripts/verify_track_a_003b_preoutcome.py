#!/usr/bin/env python3
"""Verify the Track A 003b adapter/runtime pre-outcome freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "audits" / "track-a-003b" / "PRE_OUTCOME_RUNTIME.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze["status"] != "frozen_before_acquired_candidate_execution":
        raise ValueError("pre-outcome status changed")
    for pin in freeze["source_pins"]:
        path = (ROOT / pin["path"]).resolve()
        if ROOT not in path.parents or not path.is_file() or sha256(path) != pin["sha256"]:
            raise ValueError(f"source pin mismatch: {pin['path']}")

    manifests = freeze["prepared_bundles"]["candidate_manifests_in_frozen_order"]
    if len(manifests) != 13 or len({item["candidate_id"] for item in manifests}) != 13:
        raise ValueError("candidate manifest order is incomplete")
    if freeze["prepared_bundles"]["candidate_count"] != 13:
        raise ValueError("prepared candidate count changed")
    if freeze["prepared_bundles"]["candidate_code_executed_while_preparing"]:
        raise ValueError("bundle preparation is not pre-outcome")
    if freeze["prepared_bundles"]["session_or_post_p0_state_included"]:
        raise ValueError("forbidden session state is included")
    if any(freeze["execution_boundary"].values()):
        raise ValueError("pre-outcome execution boundary was crossed")

    print(
        json.dumps(
            {
                "audit_id": freeze["audit_id"],
                "candidate_manifests": len(manifests),
                "runtime_image_id": freeze["runtime"]["runtime_image_id"],
                "source_pins": len(freeze["source_pins"]),
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
