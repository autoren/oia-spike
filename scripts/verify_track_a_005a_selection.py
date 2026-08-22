#!/usr/bin/env python3
"""Verify a committed Track A 005a header-only selection when present."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
RESULT_PATH = AUDIT_ROOT / "SOURCE_UNIVERSE_SELECTION.json"


def main() -> None:
    if not RESULT_PATH.exists():
        print(json.dumps({"audit_id": "OIA-1-TRACK-A-005a", "status": "preselection"}))
        return
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import inventory_track_a_005a_source as inventory

    universe = result["source_universe"]
    selection = result["selection"]
    if result["status"] != "held_out_source_selected_from_headers_only":
        raise ValueError("selection status changed")
    if tuple(universe["runs"]) != inventory.EXPECTED_RUNS:
        raise ValueError("selected source run roots changed")
    if universe["game_count_per_run"] != inventory.EXPECTED_GAME_COUNT:
        raise ValueError("source game count changed")
    if universe["p0_triplet_complete_for_every_run_game"] is not True:
        raise ValueError("P0 path coverage is incomplete")
    games = universe["games"]
    if len(games) != len(set(games)) or games != sorted(games):
        raise ValueError("source game universe is not canonical")
    if selection["excluded_games"] != list(inventory.EXCLUDED_GAMES):
        raise ValueError("opened-game exclusion changed")
    ranking = selection["ranking"]
    recomputed = sorted(
        (
            {"game": game, "selection_token": inventory.selection_token(game)}
            for game in games
            if game not in inventory.EXCLUDED_GAMES
        ),
        key=lambda row: (row["selection_token"], row["game"]),
    )
    if ranking != recomputed or selection["eligible_game_count"] != len(recomputed):
        raise ValueError("selection ranking is not reproducible")
    if selection["selected_game"] != recomputed[0]["game"]:
        raise ValueError("selected game is not the frozen minimum token")
    if selection["selected_token"] != recomputed[0]["selection_token"]:
        raise ValueError("selected token mismatch")
    if result["access_accounting"] != {
        "behavioral_traces_read": 0,
        "candidate_files_read": 0,
        "candidate_processes": 0,
        "member_names_read": True,
        "member_payloads_extracted": 0,
        "model_or_api_calls": 0,
        "oia_processes": 0,
        "p0_payloads_read": 0,
        "real_arc_actions": 0,
        "scores_read": 0,
        "tar_headers_read": True,
    }:
        raise ValueError("selection access accounting changed")
    digest = hashlib.sha256(RESULT_PATH.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "audit_id": inventory.AUDIT_ID,
                "pass": True,
                "result_sha256": digest,
                "selected_game": selection["selected_game"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
