#!/usr/bin/env python3
"""Verify the frozen local-Qwen/Tycho engineering qualification protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "integrations/tycho-local-qwen/QUALIFICATION_PROTOCOL.json"
MAINTENANCE = ROOT / "integrations/tycho-local-qwen/QUALIFICATION_MAINTENANCE.json"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("qualification protocol root must be an object")
    return value


def validate_protocol(path: Path = PROTOCOL) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != "OIA-TYCHO-LOCAL-QWEN-QUALIFICATION-0.1":
        raise ValueError("local-Qwen qualification schema changed")
    source = payload.get("source") or {}
    if (
        source.get("commit") != "f68912a764372ead0a610db2e1c011d41ce5197e"
        or source.get("tree") != "d5ff6a4e142934ceb865e403e3aa92d80bfa245c"
        or source.get("license") != "Apache-2.0"
        or source.get("tracked_source_must_be_clean") is not True
    ):
        raise ValueError("Tycho source boundary changed")
    model = payload.get("model") or {}
    if (
        model.get("revision") != "b869816e657114167518d41ef84c8ece43d102d7"
        or model.get("license") != "Apache-2.0"
        or model.get("model_file", {}).get("sha256")
        != "2fff409d4a22e0cb11fb0ecfafed1c669b9808f7e6bc499036c6e85297f14f4d"
        or model.get("model_file", {}).get("size") != 29787701792
        or model.get("vision_projector", {}).get("sha256")
        != "fdc443e974cad1f61c45af1cfd5580855855ddce0d6c14cc500a5714c486ac1d"
        or model.get("vision_projector", {}).get("size") != 1842940480
    ):
        raise ValueError("local-Qwen model boundary changed")
    prefreeze = payload.get("prefreeze_engineering_observation") or {}
    if prefreeze.get("model_calls") != 1 or not prefreeze.get(
        "expected_tool_call_observed"
    ):
        raise ValueError("prefreeze observation accounting changed")
    execution = payload.get("authorized_execution") or {}
    expected = {
        "transport_calls": 1,
        "public_game_model_calls_maximum": 2,
        "public_game_tool_steps_maximum": 2,
        "public_game_committed_actions_maximum": 2,
        "public_game_initial_resets_maximum": 1,
        "game_base_id": "tr87",
        "game_seed": 0,
        "tycho_config": "configs/smoke/minimal.yaml",
        "tycho_policy": "no_world_model",
        "animation_summary_calls": 0,
        "registered_arc_credentials": 0,
        "paid_model_or_api_calls": 0,
        "semi_private_or_private_games": 0,
        "competition_submissions": 0,
        "world_models_generated": 0,
        "oia_runs": 0,
    }
    for field, expected_value in expected.items():
        if execution.get(field) != expected_value:
            raise ValueError(f"qualification execution boundary changed: {field}")
    if payload.get("allowed_verdicts") != [
        "local_qwen_transport_and_opened_harness_qualification_pass",
        "local_qwen_transport_or_opened_harness_blocker",
        "qualification_boundary_violation",
    ]:
        raise ValueError("qualification verdict vocabulary changed")
    claims = payload.get("claim_boundary") or {}
    if (
        claims.get("project_reopening_effect") != "none"
        or "constructive executable-world-model generation"
        not in claims.get("does_not_support", [])
        or "semi-private or private transfer"
        not in claims.get("does_not_support", [])
        or "Track B claims" not in claims.get("does_not_support", [])
    ):
        raise ValueError("qualification claim boundary changed")
    if payload.get("status") != "frozen_unexecuted":
        raise ValueError("qualification prospective status changed")
    return payload


def validate_maintenance(path: Path = MAINTENANCE) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != (
        "OIA-TYCHO-LOCAL-QWEN-QUALIFICATION-MAINTENANCE-0.1"
    ):
        raise ValueError("local-Qwen maintenance schema changed")
    if (
        payload.get("parent_protocol")
        != "integrations/tycho-local-qwen/QUALIFICATION_PROTOCOL.json"
        or payload.get("parent_freeze_commit")
        != "ecedcc0f527181d8462986dae6121b9a7d3c0d19"
    ):
        raise ValueError("local-Qwen maintenance parent changed")
    attempts = payload.get("premaintenance_attempts") or []
    if len(attempts) != 2:
        raise ValueError("premaintenance attempt accounting changed")
    for attempt in attempts:
        if (
            attempt.get("tracked_source_clean") is not True
            or attempt.get("model_calls") != 0
            or attempt.get("resets") != 0
            or attempt.get("committed_actions") != 0
        ):
            raise ValueError("maintenance followed qualification behavior")
    correction = payload.get("single_correction") or {}
    if correction != {
        "environment_variable": "TYCHO_MAX_INFERENCE_COST_PER_GAME",
        "old_value": "0.50",
        "new_value": "0",
        "meaning": (
            "Disable only dollar accounting for the local backend; retain the "
            "exact two-call and two-tool-step ceilings."
        ),
    }:
        raise ValueError("local-Qwen maintenance correction changed")
    boundaries = payload.get("unchanged_boundaries") or {}
    expected = {
        "transport_calls": 1,
        "public_game_model_calls_maximum": 2,
        "public_game_tool_steps_maximum": 2,
        "public_game_committed_actions_maximum": 2,
        "public_game_initial_resets_maximum": 1,
        "game_base_id": "tr87",
        "game_seed": 0,
        "registered_arc_credentials": 0,
        "paid_model_or_api_calls": 0,
        "semi_private_or_private_games": 0,
        "competition_submissions": 0,
        "world_models_generated": 0,
        "oia_runs": 0,
        "project_reopening_effect": "none",
    }
    if boundaries != expected:
        raise ValueError("local-Qwen maintenance boundary changed")
    if payload.get("status") != "maintenance_frozen_unexecuted":
        raise ValueError("local-Qwen maintenance status changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    args = parser.parse_args()
    payload = validate_protocol(args.protocol)
    maintenance = validate_maintenance()
    print(
        json.dumps(
            {
                "game": payload["authorized_execution"]["game_base_id"],
                "project_reopening_effect": "none",
                "maintenance_status": maintenance["status"],
                "status": "tycho_local_qwen_qualification_protocol_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
