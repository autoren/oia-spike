#!/usr/bin/env python3
"""Verify the frozen local-Qwen final commit-only smoke boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "integrations/tycho-local-qwen/FINAL_COMMIT_PROTOCOL.json"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("final-commit protocol root must be an object")
    return value


def validate_protocol(path: Path = PROTOCOL) -> dict[str, Any]:
    payload = load_object(path)
    if payload.get("schema_version") != "OIA-TYCHO-LOCAL-QWEN-FINAL-COMMIT-0.1":
        raise ValueError("final-commit protocol schema changed")
    parent = payload.get("parent_blocker") or {}
    if (
        parent.get("commit") != "cefff0398b68c29324b6be9a07b0c851d85a4e48"
        or parent.get("result_sha256")
        != "637c9a4dab46549b2b4c2b693cd5d6f54f95a35af8661dd53cd8a59d89dc5878"
        or "unreachable" not in parent.get("diagnosis", "")
    ):
        raise ValueError("final-commit parent blocker changed")
    pins = payload.get("unchanged_pins") or {}
    expected_pins = {
        "tycho_commit": "f68912a764372ead0a610db2e1c011d41ce5197e",
        "tycho_tree": "d5ff6a4e142934ceb865e403e3aa92d80bfa245c",
        "agent_source_sha256": "38472ec280187305db3fd2325fb1197c28ac31b3e22c13d169b4aaa86daaf7dc",
        "model_revision": "b869816e657114167518d41ef84c8ece43d102d7",
        "model_sha256": "2fff409d4a22e0cb11fb0ecfafed1c669b9808f7e6bc499036c6e85297f14f4d",
        "projector_sha256": "fdc443e974cad1f61c45af1cfd5580855855ddce0d6c14cc500a5714c486ac1d",
        "runtime_identifier": "qwen3.6-27b-oia",
        "endpoint": "http://127.0.0.1:1234/v1",
        "resolved_game_id": "tr87-cd924810",
        "game_seed": 0,
        "source_metadata_sha256": "ef53168a70367e3675ed7c9e938856b4345a02a2dc562836caf21a55c4ef0f03",
        "source_program_sha256": "3274657a6499af5c7a52390d58a5c5441497ed70b84388e418fdfa6c9601e305",
        "tycho_config": "configs/smoke/minimal.yaml",
        "tycho_policy": "no_world_model",
        "operation_mode": "offline",
        "public_game_tool_steps_per_turn_maximum": 4,
        "max_tokens_per_model_call": 2048,
        "docker_image": "tycho-python-sandbox:0.2",
    }
    if pins != expected_pins:
        raise ValueError("final-commit source/model/game pins changed")
    if payload.get("single_change") != {
        "public_game_model_calls_maximum": {"old": 4, "new": 5},
        "purpose": (
            "Reserve exactly one call after four tool responses for Tycho's "
            "existing final commit-only prompt."
        ),
        "source_guard": "No Tycho patch or prompt change is permitted.",
    }:
        raise ValueError("final-commit single change changed")
    execution = payload.get("authorized_execution") or {}
    expected_execution = {
        "runs": 1,
        "public_game_model_calls_maximum": 5,
        "public_game_tool_steps_per_turn_maximum": 4,
        "public_game_environment_actions_maximum": 1,
        "public_game_reset_actions_maximum": 0,
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
        raise ValueError("final-commit execution boundary changed")
    condition = payload.get("pass_condition") or {}
    if (
        condition.get("required_tool_trace")
        != {"tool": "take_action", "committed": True, "final_commit": True}
        or condition.get("tycho_default_actions_are_not_successes") is not True
        or condition.get("correctness_or_progress_required") is not False
    ):
        raise ValueError("final-commit pass condition changed")
    if payload.get("allowed_verdicts") != [
        "local_qwen_final_commit_pass",
        "local_qwen_final_commit_blocker",
        "final_commit_boundary_violation",
    ]:
        raise ValueError("final-commit verdict vocabulary changed")
    claims = payload.get("claim_boundary") or {}
    if (
        claims.get("project_reopening_effect") != "none"
        or "correct action selection" not in claims.get("does_not_support", [])
        or "Track B claims" not in claims.get("does_not_support", [])
    ):
        raise ValueError("final-commit claim boundary changed")
    if "Do not raise either ceiling again" not in payload.get("stopping_rule", ""):
        raise ValueError("final-commit stopping rule changed")
    if payload.get("status") != "frozen_unexecuted":
        raise ValueError("final-commit prospective status changed")
    return payload


def main() -> None:
    payload = validate_protocol()
    print(
        json.dumps(
            {
                "game": payload["unchanged_pins"]["resolved_game_id"],
                "model_calls_maximum": 5,
                "tool_steps_maximum": 4,
                "status": "tycho_local_qwen_final_commit_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
