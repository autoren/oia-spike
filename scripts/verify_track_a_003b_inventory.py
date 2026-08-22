#!/usr/bin/env python3
"""Verify the committed Track A 003b inventory and frozen next-gate pins."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-003b"
INVENTORY_PATH = AUDIT_ROOT / "CHECKPOINT_INVENTORY.json"
PROTOCOL_PATH = AUDIT_ROOT / "LOCAL_ADMISSION_PROTOCOL.frozen.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_repo_path(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file() or ROOT not in path.resolve().parents:
        raise ValueError(f"invalid repository file pin: {relative!r}")
    return path


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    if inventory.get("status") != "inventory_complete_admission_not_run":
        raise ValueError("inventory status broadens or changes the recorded result")
    if inventory.get("execution_boundary") != {
        "arc_execution": False,
        "candidate_execution": False,
        "credential_use": False,
        "model_or_api_call": False,
        "network_or_service_call": False,
        "oia_separability": False,
    }:
        raise ValueError("unexpected inventory execution boundary")

    opened = inventory["opened_prefix"]
    if not all(
        (
            opened["all_candidate_p0_bytes_identical"],
            opened["all_candidate_metadata_exact"],
            opened["released_environment_ids_identical"],
        )
    ):
        raise ValueError("opened-prefix identity precondition is not satisfied")
    if opened["candidate_record_count"] != 13:
        raise ValueError("unexpected candidate-record count")

    order = inventory["candidate_order"]
    checkpoints = order["retained_checkpoints_round_robin"]
    if order["final_worktrees_first"] != ["max/final", "xhigh/final"]:
        raise ValueError("final-worktree order changed")
    if order["total_exact_retained_checkpoint_commits"] != 11 or len(checkpoints) != 11:
        raise ValueError("unexpected retained-checkpoint count")
    if len({item["commit"] for item in checkpoints}) != 11:
        raise ValueError("retained checkpoint commits are not unique")

    for pin_name in ("source_inventory",):
        pin = protocol[pin_name]
        if sha256(resolve_repo_path(pin["path"])) != pin["sha256"]:
            raise ValueError(f"protocol pin mismatch: {pin_name}")
    for pin_name, pin in protocol["inherited_rules"].items():
        if not isinstance(pin, dict) or "path" not in pin:
            continue
        if sha256(resolve_repo_path(pin["path"])) != pin["sha256"]:
            raise ValueError(f"inherited protocol pin mismatch: {pin_name}")

    if protocol["finite_boundary"]["word_count"] != 84:
        raise ValueError("finite action-word boundary changed")
    if protocol["success_condition"].split()[0] != "candidate_frontier_feasible":
        raise ValueError("unexpected success condition")

    print(
        json.dumps(
            {
                "audit_id": inventory["audit_id"],
                "candidate_records": opened["candidate_record_count"],
                "inventory_sha256": sha256(INVENTORY_PATH),
                "retained_checkpoints": len(checkpoints),
                "word_count": protocol["finite_boundary"]["word_count"],
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
