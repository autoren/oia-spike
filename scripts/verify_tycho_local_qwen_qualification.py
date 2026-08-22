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
RESULT = ROOT / "integrations/tycho-local-qwen/QUALIFICATION_RESULT.json"


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


def validate_result(path: Path = RESULT) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != (
        "OIA-TYCHO-LOCAL-QWEN-QUALIFICATION-RESULT-0.1"
    ):
        raise ValueError("local-Qwen qualification result schema changed")
    expected_commits = {
        "protocol_commit": "ecedcc0f527181d8462986dae6121b9a7d3c0d19",
        "transport_driver_commit": "0dd3192fbd1025c7031acca884a3221473ea2513",
        "maintenance_commit": "36007e279e982ade75a0ec7e083380ba27b3b8f8",
    }
    for field, expected in expected_commits.items():
        if payload.get(field) != expected:
            raise ValueError(f"qualification result freeze changed: {field}")
    source = payload.get("source") or {}
    if (
        source.get("commit") != "f68912a764372ead0a610db2e1c011d41ce5197e"
        or source.get("tree") != "d5ff6a4e142934ceb865e403e3aa92d80bfa245c"
        or source.get("tracked_source_clean_at_qualifying_run") is not True
    ):
        raise ValueError("qualification result source changed")
    transport = payload.get("postfreeze_transport") or {}
    if transport != {
        "calls": 1,
        "input_tokens": 375,
        "output_tokens": 169,
        "tool_name": "report_transport_ok",
        "tool_arguments": {"status": "ok"},
        "pass": True,
    }:
        raise ValueError("qualification transport result changed")
    result = payload.get("public_harness_result") or {}
    maximums = {
        "model_calls": 2,
        "tool_steps": 2,
        "environment_actions_recorded": 2,
        "reported_reset_actions": 1,
    }
    for field, maximum in maximums.items():
        value = result.get(field)
        if not isinstance(value, int) or value < 0 or value > maximum:
            raise ValueError(f"qualification result exceeded boundary: {field}")
    expected_zeroes = [
        "model_selected_actions",
        "registered_arc_credentials",
        "paid_model_or_api_calls",
        "semi_private_or_private_games",
        "competition_submissions",
        "world_models_generated",
        "oia_runs",
    ]
    if any(result.get(field) != 0 for field in expected_zeroes):
        raise ValueError("qualification result crossed a zero boundary")
    if (
        result.get("resolved_game_id") != "tr87-cd924810"
        or result.get("source_metadata", {}).get("sha256")
        != "ef53168a70367e3675ed7c9e938856b4345a02a2dc562836caf21a55c4ef0f03"
        or result.get("source_program", {}).get("sha256")
        != "3274657a6499af5c7a52390d58a5c5441497ed70b84388e418fdfa6c9601e305"
        or result.get("run_spec_fingerprint")
        != "b7b6ca829d25efd9de67acfd081d676cd0218673ded86154640c913258f0dba5"
        or result.get("stop_reason") != "llm_call_limit"
    ):
        raise ValueError("qualification public-harness evidence changed")
    if (
        result.get("environment_action_sequence") != ["ACTION1"]
        or result.get("defaulted_actions") != 1
        or result.get("default_reason") != "default (tool cap)"
        or result.get("action_selection_by_model_established") is not False
    ):
        raise ValueError("qualification action attribution changed")
    if payload.get("verdict") != (
        "local_qwen_transport_and_opened_harness_qualification_pass"
    ):
        raise ValueError("qualification result verdict changed")
    claims = payload.get("claim_boundary") or {}
    if any(value is not False for value in claims.values()):
        raise ValueError("qualification result claim boundary broadened")
    next_gate = payload.get("next_gate") or {}
    if next_gate.get("status") != "not_authorized_by_this_result":
        raise ValueError("qualification result authorized a successor")
    if payload.get("status") != "completed":
        raise ValueError("qualification result status changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    args = parser.parse_args()
    payload = validate_protocol(args.protocol)
    maintenance = validate_maintenance()
    result = validate_result()
    print(
        json.dumps(
            {
                "game": payload["authorized_execution"]["game_base_id"],
                "project_reopening_effect": "none",
                "maintenance_status": maintenance["status"],
                "verdict": result["verdict"],
                "status": "tycho_local_qwen_qualification_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
