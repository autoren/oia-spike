#!/usr/bin/env python3
"""Select a held-out Track A 005a game from tar headers only."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Iterable


AUDIT_ID = "OIA-1-TRACK-A-005a"
EXPECTED_ARCHIVE_SIZE = 797_835_543
EXPECTED_ARCHIVE_MD5 = "4dd279f099609392c30cffa468801316"
EXPECTED_ARCHIVE_SHA256 = "c3d85c4a75170de08837b9fc63cb7a7dde389b1205ca71b9f0fed16a9c09cf93"
EXPECTED_RUNS = (
    "ewma_v1.5_sv_gpt-5.5_xhigh_run1",
    "ewma_v1.6_sv_gpt-5.6-sol_max_run1",
    "ewma_v1.6_sv_gpt-5.6-sol_xhigh_run1",
    "twma_v1.6_gpt-5.6-sol_max_run1",
    "twma_v1.6_gpt-5.6-sol_xhigh_run1",
)
EXCLUDED_GAMES = ("ls20",)
P0_FILENAMES = ("initial_frame.png", "initial_frame.txt", "initial_metadata.json")
P0_PREFIX_PARTS = ("run", "agent_run", "client", "session", "level_01_attempt_01")
EXPECTED_GAME_COUNT = 25


@dataclass(frozen=True)
class Member:
    name: str
    kind: str
    size: int


def file_hashes(path: Path) -> tuple[int, str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def safe_parts(name: str) -> tuple[str, ...]:
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe tar member name: {name!r}")
    return tuple(part for part in pure.parts if part not in ("", "."))


def selection_token(game: str) -> str:
    payload = f"{AUDIT_ID}\0{EXPECTED_ARCHIVE_SHA256}\0{game}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inventory_members(
    members: Iterable[Member],
    *,
    expected_game_count: int = EXPECTED_GAME_COUNT,
) -> dict[str, object]:
    run_games: dict[str, set[str]] = {run: set() for run in EXPECTED_RUNS}
    p0_files: dict[tuple[str, str], set[str]] = {}
    p0_paths: dict[tuple[str, str, str], str] = {}
    kind_counts: dict[str, int] = {}
    member_count = 0
    member_name_hasher = hashlib.sha256()
    total_regular_bytes = 0

    for member in members:
        parts = safe_parts(member.name)
        member_count += 1
        kind_counts[member.kind] = kind_counts.get(member.kind, 0) + 1
        member_name_hasher.update(member.name.encode("utf-8") + b"\n")
        if member.kind == "file":
            total_regular_bytes += member.size
        if len(parts) < 4 or parts[0] != "runs_additional":
            continue
        run, game = parts[1], parts[2]
        if run not in run_games:
            raise ValueError(f"unexpected run root: {run}")
        if not (len(game) == 4 and game.isalnum() and game == game.lower()):
            raise ValueError(f"invalid game root: {game}")
        run_games[run].add(game)
        expected_prefix = ("runs_additional", run, game) + P0_PREFIX_PARTS
        if parts[:-1] == expected_prefix and parts[-1] in P0_FILENAMES:
            if member.kind != "file":
                raise ValueError(f"P0 member is not a regular file: {member.name}")
            key = (run, game)
            if parts[-1] in p0_files.setdefault(key, set()):
                raise ValueError(f"duplicate P0 member: {member.name}")
            p0_files[key].add(parts[-1])
            p0_paths[(run, game, parts[-1])] = member.name

    discovered_runs = tuple(sorted(run for run, games in run_games.items() if games))
    if discovered_runs != EXPECTED_RUNS:
        raise ValueError(f"run roots changed: {discovered_runs}")
    game_sets = list(run_games.values())
    if any(len(games) != expected_game_count for games in game_sets):
        raise ValueError("per-run game count changed")
    common_games = set.intersection(*game_sets)
    if any(games != common_games for games in game_sets):
        raise ValueError("run roots do not contain one identical game universe")

    eligible: list[str] = []
    rejected: list[dict[str, object]] = []
    for game in sorted(common_games):
        reasons: list[str] = []
        if game in EXCLUDED_GAMES:
            reasons.append("previously_opened_game")
        missing_runs = [
            run
            for run in EXPECTED_RUNS
            if p0_files.get((run, game), set()) != set(P0_FILENAMES)
        ]
        if missing_runs:
            reasons.append("incomplete_common_level_1_p0")
        if reasons:
            rejected.append({"game": game, "reasons": reasons, "missing_p0_runs": missing_runs})
        else:
            eligible.append(game)
    if not eligible:
        raise ValueError("no eligible held-out game remains")

    ranking = sorted(
        ({"game": game, "selection_token": selection_token(game)} for game in eligible),
        key=lambda row: (row["selection_token"], row["game"]),
    )
    selected = ranking[0]
    selected_game = str(selected["game"])
    selected_p0_paths = {
        run: {
            filename: p0_paths[(run, selected_game, filename)]
            for filename in P0_FILENAMES
        }
        for run in EXPECTED_RUNS
    }
    return {
        "schema_version": 1,
        "audit_id": AUDIT_ID,
        "status": "held_out_source_selected_from_headers_only",
        "archive": {
            "sha256": EXPECTED_ARCHIVE_SHA256,
            "member_count": member_count,
            "member_name_index_sha256": member_name_hasher.hexdigest(),
            "kind_counts": dict(sorted(kind_counts.items())),
            "total_regular_file_bytes": total_regular_bytes,
        },
        "source_universe": {
            "runs": list(EXPECTED_RUNS),
            "game_count_per_run": len(common_games),
            "games": sorted(common_games),
            "p0_triplet_complete_for_every_run_game": all(
                p0_files.get((run, game), set()) == set(P0_FILENAMES)
                for run in EXPECTED_RUNS
                for game in common_games
            ),
        },
        "selection": {
            "excluded_games": list(EXCLUDED_GAMES),
            "eligible_game_count": len(eligible),
            "ranking": ranking,
            "selected_game": selected_game,
            "selected_token": selected["selection_token"],
            "selected_p0_paths": selected_p0_paths,
            "rejected": rejected,
        },
        "access_accounting": {
            "tar_headers_read": True,
            "member_names_read": True,
            "member_payloads_extracted": 0,
            "p0_payloads_read": 0,
            "candidate_files_read": 0,
            "behavioral_traces_read": 0,
            "scores_read": 0,
            "candidate_processes": 0,
            "oia_processes": 0,
            "real_arc_actions": 0,
            "model_or_api_calls": 0,
        },
        "claim_boundary": (
            "Held-out source selection from archive headers only; no P0 content, "
            "candidate code, behavior, score, OIA, model, or real environment outcome."
        ),
    }


def tar_members(path: Path) -> Iterable[Member]:
    with tarfile.open(path, mode="r:gz") as archive:
        for item in archive:
            if item.isfile():
                kind = "file"
            elif item.isdir():
                kind = "directory"
            elif item.issym():
                kind = "symlink"
            elif item.islnk():
                kind = "hardlink"
            else:
                kind = "other"
            yield Member(item.name, kind, item.size)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    archive = args.archive.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite selection result: {output}")
    observed = file_hashes(archive)
    expected = (EXPECTED_ARCHIVE_SIZE, EXPECTED_ARCHIVE_MD5, EXPECTED_ARCHIVE_SHA256)
    if observed != expected:
        raise ValueError(f"archive identity mismatch: {observed}")
    result = inventory_members(tar_members(archive))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "audit_id": AUDIT_ID,
                "eligible_game_count": result["selection"]["eligible_game_count"],
                "output": str(output),
                "selected_game": result["selection"]["selected_game"],
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
