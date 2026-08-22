#!/usr/bin/env python3
"""Verify the prospective local-Qwen explicit-action smoke boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "integrations/tycho-local-qwen/ACTION_SELECTION_PROTOCOL.json"
RESULT = ROOT / "integrations/tycho-local-qwen/ACTION_SELECTION_RESULT.json"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("action-selection protocol root must be an object")
    return value


def validate_protocol(path: Path = PROTOCOL) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != "OIA-TYCHO-LOCAL-QWEN-ACTION-SELECTION-0.1":
        raise ValueError("action-selection protocol schema changed")
    parent = payload.get("parent_evidence") or {}
    if (
        parent.get("merge_commit")
        != "031d895f3cd229ac354871aaed10ab32246bb966"
        or parent.get("result_sha256")
        != "1cb018e92cc5a19e54abe735647d48ba9ff1586e6612a4fe2fc1a18fea87138f"
    ):
        raise ValueError("action-selection parent evidence changed")
    pins = payload.get("unchanged_pins") or {}
    expected_pins = {
        "tycho_commit": "f68912a764372ead0a610db2e1c011d41ce5197e",
        "tycho_tree": "d5ff6a4e142934ceb865e403e3aa92d80bfa245c",
        "model_revision": "b869816e657114167518d41ef84c8ece43d102d7",
        "model_sha256": "2fff409d4a22e0cb11fb0ecfafed1c669b9808f7e6bc499036c6e85297f14f4d",
        "projector_sha256": "fdc443e974cad1f61c45af1cfd5580855855ddce0d6c14cc500a5714c486ac1d",
        "runtime_identifier": "qwen3.6-27b-oia",
        "endpoint": "http://127.0.0.1:1234/v1",
        "game_base_id": "tr87",
        "resolved_game_id": "tr87-cd924810",
        "game_seed": 0,
        "source_metadata_sha256": "ef53168a70367e3675ed7c9e938856b4345a02a2dc562836caf21a55c4ef0f03",
        "source_program_sha256": "3274657a6499af5c7a52390d58a5c5441497ed70b84388e418fdfa6c9601e305",
        "tycho_config": "configs/smoke/minimal.yaml",
        "tycho_policy": "no_world_model",
        "docker_image": "tycho-python-sandbox:0.2",
    }
    if pins != expected_pins:
        raise ValueError("action-selection source/model/game pins changed")
    relaxation = payload.get("sole_behavioral_relaxation") or {}
    if (
        relaxation.get("public_game_model_calls_maximum") != {"old": 2, "new": 4}
        or relaxation.get("public_game_tool_steps_per_turn_maximum")
        != {"old": 2, "new": 4}
    ):
        raise ValueError("action-selection relaxation changed")
    execution = payload.get("authorized_execution") or {}
    expected_execution = {
        "runs": 1,
        "operation_mode": "offline_use_exact_existing_public_source",
        "public_game_model_calls_maximum": 4,
        "public_game_tool_steps_per_turn_maximum": 4,
        "public_game_environment_actions_maximum": 4,
        "public_game_reset_actions_maximum": 1,
        "max_tokens_per_model_call": 2048,
        "animation_summary_calls": 0,
        "registered_arc_credentials": 0,
        "paid_model_or_api_calls": 0,
        "public_source_downloads": 0,
        "semi_private_or_private_games": 0,
        "competition_submissions": 0,
        "world_models_generated": 0,
        "oia_runs": 0,
    }
    if execution != expected_execution:
        raise ValueError("action-selection execution boundary changed")
    condition = payload.get("pass_condition") or {}
    if (
        condition.get("default_actions_are_not_successes") is not True
        or condition.get("level_completion_required") is not False
        or condition.get("reward_or_score_improvement_required") is not False
        or "reasoning.src" not in condition.get("model_selected_action_rule", "")
    ):
        raise ValueError("action-selection pass condition changed")
    if payload.get("allowed_verdicts") != [
        "local_qwen_explicit_public_action_selection_pass",
        "local_qwen_explicit_public_action_selection_blocker",
        "action_selection_boundary_violation",
    ]:
        raise ValueError("action-selection verdict vocabulary changed")
    claims = payload.get("claim_boundary") or {}
    if (
        claims.get("project_reopening_effect") != "none"
        or "correct action selection" not in claims.get("does_not_support", [])
        or "semi-private or private transfer"
        not in claims.get("does_not_support", [])
        or "Track B claims" not in claims.get("does_not_support", [])
    ):
        raise ValueError("action-selection claim boundary changed")
    if payload.get("status") != "frozen_unexecuted":
        raise ValueError("action-selection prospective status changed")
    return payload


def validate_result(path: Path = RESULT) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != (
        "OIA-TYCHO-LOCAL-QWEN-ACTION-SELECTION-RESULT-0.1"
    ):
        raise ValueError("action-selection result schema changed")
    if payload.get("protocol_commit") != (
        "9d2310e054b62429ec2b43aa71ac9194032669ad"
    ):
        raise ValueError("action-selection result freeze changed")
    source = payload.get("source") or {}
    if (
        source.get("tycho_commit")
        != "f68912a764372ead0a610db2e1c011d41ce5197e"
        or source.get("tycho_tree")
        != "d5ff6a4e142934ceb865e403e3aa92d80bfa245c"
        or source.get("agent_source_sha256")
        != "38472ec280187305db3fd2325fb1197c28ac31b3e22c13d169b4aaa86daaf7dc"
        or source.get("tracked_source_clean") is not True
    ):
        raise ValueError("action-selection result source changed")
    execution = payload.get("execution") or {}
    expected_exact = {
        "runs": 1,
        "operation_mode": "offline",
        "game_id": "tr87-cd924810",
        "seed": 0,
        "run_spec_fingerprint": "d86f81da0f7740c8ee66963c946fe02f41127a4ab64626ae99c7155136cc683e",
        "model_calls": 4,
        "tool_steps": 4,
        "environment_actions_recorded": 1,
        "environment_action_sequence": ["ACTION1"],
        "model_selected_non_reset_actions": 0,
        "defaulted_actions": 1,
        "default_reason": "default (tool cap)",
        "explicit_action_selection_established": False,
    }
    for field, expected in expected_exact.items():
        if execution.get(field) != expected:
            raise ValueError(f"action-selection result changed: {field}")
    zero_boundaries = [
        "reset_actions",
        "paid_model_or_api_calls",
        "public_source_downloads",
        "semi_private_or_private_games",
        "competition_submissions",
        "world_models_generated",
        "oia_runs",
    ]
    if any(execution.get(field) != 0 for field in zero_boundaries):
        raise ValueError("action-selection result crossed a zero boundary")
    if payload.get("verdict") != (
        "local_qwen_explicit_public_action_selection_blocker"
    ):
        raise ValueError("action-selection result verdict changed")
    interpretation = payload.get("interpretation") or {}
    if (
        "max_calls equal to max_tool_steps"
        not in interpretation.get("configuration_diagnosis", "")
        or interpretation.get("project_reopening_effect") != "none"
    ):
        raise ValueError("action-selection diagnosis changed")
    next_gate = payload.get("next_gate") or {}
    if (
        next_gate.get("name") != "local_qwen_final_commit_pass_smoke"
        or next_gate.get("status") != "requires_separate_freeze"
    ):
        raise ValueError("action-selection next gate changed")
    claims = payload.get("claim_boundary") or {}
    if any(value is not False for value in claims.values()):
        raise ValueError("action-selection result claim boundary broadened")
    if payload.get("status") != "completed":
        raise ValueError("action-selection result status changed")
    return payload


def main() -> None:
    payload = validate_protocol()
    result = validate_result()
    print(
        json.dumps(
            {
                "game": payload["unchanged_pins"]["resolved_game_id"],
                "model_calls_maximum": 4,
                "project_reopening_effect": "none",
                "verdict": result["verdict"],
                "status": "tycho_local_qwen_action_selection_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
