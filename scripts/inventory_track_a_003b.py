#!/usr/bin/env python3
"""Inventory the acquired Track A 003b run trees without executing candidates."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


RUNS = (
    {
        "published_run_id": "ewma_sv_v1.6_gpt-5.6-sol_max_run1",
        "archive_run_root": "ewma_v1.6_sv_gpt-5.6-sol_max_run1",
        "short_id": "max",
    },
    {
        "published_run_id": "ewma_sv_v1.6_gpt-5.6-sol_xhigh_run1",
        "archive_run_root": "ewma_v1.6_sv_gpt-5.6-sol_xhigh_run1",
        "short_id": "xhigh",
    },
)

P0_PATHS = (
    "client/session/level_01_attempt_01/initial_frame.png",
    "client/session/level_01_attempt_01/initial_frame.txt",
    "client/session/level_01_attempt_01/initial_metadata.json",
)

CORE_PATHS = (
    "game_status.py",
    "session_tools.py",
    "state_reconstruction_tools.py",
    "world_model_engine.py",
    "world_model_state_io.py",
)

CANDIDATE_RELEVANT_NAMES = frozenset(
    CORE_PATHS
    + (
        "world_model.md",
        "world_model_guided_search.py",
        "world_model_main_planner.py",
        "world_model_position_planner.py",
    )
)

EXPECTED_METADATA = {
    "action_input": {"data": {}, "id": "RESET"},
    "available_actions": [1, 2, 3, 4],
    "levels_completed": 0,
    "state": "NOT_FINISHED",
    "step_index": 0,
    "win_levels": 7,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", f"--git-dir={root / '.git'}", f"--work-tree={root}", *args),
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_text(root: Path, *args: str) -> str:
    return git(root, *args).stdout.decode("utf-8", errors="strict").strip()


def git_bytes(root: Path, ref: str, path: str) -> bytes:
    return git(root, "show", f"{ref}:{path}").stdout


def parse_imports(source: bytes, label: str) -> list[str]:
    try:
        tree = ast.parse(source.decode("utf-8"), filename=label)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot statically parse {label}: {exc}") from exc
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return sorted(imports)


def tree_digest(root: Path) -> tuple[str, int, int]:
    """Hash path, length, and contents for each non-Git regular worktree file."""
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        file_hash = sha256_file(path)
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(str(size).encode("ascii") + b"\0")
        digest.update(file_hash.encode("ascii") + b"\n")
        count += 1
        total += size
    return digest.hexdigest(), count, total


def status_summary(root: Path) -> dict:
    entries = git(root, "status", "--porcelain=v1", "-z").stdout.split(b"\0")
    statuses: list[tuple[str, str]] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        if not entry:
            break
        status = entry[:2].decode("ascii")
        path = entry[3:].decode("utf-8", errors="surrogateescape")
        statuses.append((status, path))
        if "R" in status or "C" in status:
            index += 1
        index += 1
    tracked = [(status, path) for status, path in statuses if status != "??"]
    untracked = [path for status, path in statuses if status == "??"]
    relevant = sorted(
        path
        for _, path in tracked
        if Path(path).name in CANDIDATE_RELEVANT_NAMES
    )
    return {
        "clean": not statuses,
        "tracked_change_count": len(tracked),
        "untracked_path_count": len(untracked),
        "candidate_relevant_tracked_changes": relevant,
    }


def p0_from_worktree(root: Path) -> dict:
    hashes = {path: sha256_file(root / path) for path in P0_PATHS}
    metadata = json.loads((root / P0_PATHS[2]).read_text(encoding="utf-8"))
    return {
        "hashes": hashes,
        "metadata": metadata,
        "metadata_matches_frozen_reset": metadata == EXPECTED_METADATA,
    }


def p0_from_ref(root: Path, ref: str) -> dict:
    blobs = {path: git_bytes(root, ref, path) for path in P0_PATHS}
    metadata = json.loads(blobs[P0_PATHS[2]].decode("utf-8"))
    return {
        "hashes": {path: sha256_bytes(data) for path, data in blobs.items()},
        "metadata": metadata,
        "metadata_matches_frozen_reset": metadata == EXPECTED_METADATA,
    }


def core_inventory(root: Path, ref: str | None = None) -> dict:
    if ref is None:
        sources = {path: (root / path).read_bytes() for path in CORE_PATHS}
    else:
        sources = {path: git_bytes(root, ref, path) for path in CORE_PATHS}
    imports = {
        path: parse_imports(source, f"{ref or 'worktree'}:{path}")
        for path, source in sources.items()
    }
    return {
        "required_core_files_present": True,
        "core_file_sha256": {path: sha256_bytes(source) for path, source in sources.items()},
        "static_top_level_imports": imports,
    }


def tags(root: Path) -> list[tuple[int, str]]:
    names = git_text(root, "for-each-ref", "--format=%(refname:short)", "refs/tags").splitlines()
    found: list[tuple[int, str]] = []
    for name in names:
        match = re.fullmatch(r"iteration_(\d+)", name)
        if match is None:
            raise ValueError(f"unexpected retained tag: {name!r}")
        found.append((int(match.group(1)), name))
    found.sort()
    return found


def sidecars(run_parent: Path) -> dict:
    actions_path = run_parent / "ls20_actions.json"
    scorecard_path = run_parent / "ls20_scorecard.json"
    cost_path = run_parent / "ls20_cost_estimation.json"
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    environment = scorecard["environments"][0]
    return {
        "actions_count": len(actions),
        "environment_id": environment["id"],
        "level_count": environment["level_count"],
        "levels_completed": environment["levels_completed"],
        "files": {
            path.name: {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (actions_path, scorecard_path, cost_path)
        },
    }


def run_inventory(payload_root: Path, spec: dict) -> dict:
    run_parent = payload_root / "selected" / "runs_additional" / spec["archive_run_root"]
    root = run_parent / "ls20" / "run" / "agent_run"
    if not root.is_dir() or not (root / ".git").is_dir():
        raise ValueError(f"missing acquired run tree: {spec['archive_run_root']}")

    fsck = git(root, "fsck", "--full", "--no-reflogs", "--unreachable")
    if fsck.stdout or fsck.stderr:
        raise ValueError(f"Git object integrity output for {spec['archive_run_root']}")

    session_path = root / "client" / "session" / ".client_session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    worktree_hash, worktree_files, worktree_bytes = tree_digest(root)
    worktree_p0 = p0_from_worktree(root)
    retained: list[dict] = []
    for iteration, tag in tags(root):
        commit = git_text(root, "rev-parse", f"{tag}^{{commit}}")
        retained.append(
            {
                "iteration": iteration,
                "tag": tag,
                "commit": commit,
                "tree": git_text(root, "rev-parse", f"{commit}^{{tree}}"),
                "p0": p0_from_ref(root, commit),
                "core": core_inventory(root, commit),
            }
        )

    return {
        **spec,
        "git": {
            "fsck_full_no_reflogs_unreachable_pass": True,
            "head_commit": git_text(root, "rev-parse", "HEAD^{commit}"),
            "head_tree": git_text(root, "rev-parse", "HEAD^{tree}"),
            "retained_tag_count": len(retained),
        },
        "final_worktree": {
            "identity": "selected-file-manifest paths plus acquired bytes; not HEAD",
            "tree_sha256_excluding_dot_git": worktree_hash,
            "regular_file_count_excluding_dot_git": worktree_files,
            "total_bytes_excluding_dot_git": worktree_bytes,
            "status": status_summary(root),
            "p0": worktree_p0,
            "core": core_inventory(root),
        },
        "retained_checkpoints": retained,
        "released_sidecars": sidecars(run_parent),
        "session_state_risk": {
            "session_file_present": session_path.is_file(),
            "credential_field_present": "session_token" in session,
            "service_url_field_present": "server_url" in session,
            "values_recorded": False,
            "admission_rule": "exclude session state and deny network; never use released credential/service values",
        },
    }


def inventory(payload_root: Path) -> dict:
    runs = [run_inventory(payload_root, spec) for spec in RUNS]
    canonical_p0 = runs[0]["final_worktree"]["p0"]

    p0_records: list[dict] = []
    for run in runs:
        p0_records.append(run["final_worktree"]["p0"])
        p0_records.extend(checkpoint["p0"] for checkpoint in run["retained_checkpoints"])

    checkpoint_order: list[dict] = []
    maximum_iteration = max(
        checkpoint["iteration"]
        for run in runs
        for checkpoint in run["retained_checkpoints"]
    )
    for iteration in range(1, maximum_iteration + 1):
        for run in runs:
            for checkpoint in run["retained_checkpoints"]:
                if checkpoint["iteration"] == iteration:
                    checkpoint_order.append(
                        {
                            "candidate_id": f"{run['short_id']}/{checkpoint['tag']}",
                            "published_run_id": run["published_run_id"],
                            "tag": checkpoint["tag"],
                            "commit": checkpoint["commit"],
                            "tree": checkpoint["tree"],
                        }
                    )

    environment_ids = [run["released_sidecars"]["environment_id"] for run in runs]
    return {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-003b",
        "inventory_id": "agent02-attempt02-local-read-only-inventory",
        "status": "inventory_complete_admission_not_run",
        "source_artifact": {
            "github_actions_artifact_id": 9465881649,
            "artifact_zip_sha256": "1b239318741872a339e4a1a31aa3f6876ee298fdb17db328075a343d56a52a1a",
            "inner_package_sha256": "de141756be11b7d54730584ce16d3d0979a9bbd8aef707a73d50ab8a112c2cbf",
        },
        "execution_boundary": {
            "candidate_execution": False,
            "arc_execution": False,
            "network_or_service_call": False,
            "credential_use": False,
            "model_or_api_call": False,
            "oia_separability": False,
        },
        "opened_prefix": {
            "prefix_id": "ls20_P0_reset_observation",
            "canonical_p0": canonical_p0,
            "candidate_record_count": len(p0_records),
            "all_candidate_p0_bytes_identical": all(record["hashes"] == canonical_p0["hashes"] for record in p0_records),
            "all_candidate_metadata_exact": all(record["metadata"] == EXPECTED_METADATA for record in p0_records),
            "released_environment_ids": environment_ids,
            "released_environment_ids_identical": len(set(environment_ids)) == 1,
            "finite_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
        },
        "candidate_order": {
            "final_worktrees_first": [f"{run['short_id']}/final" for run in runs],
            "retained_checkpoints_round_robin": checkpoint_order,
            "total_exact_retained_checkpoint_commits": len(checkpoint_order),
            "maximum_admitted_candidates": 8,
            "behavior_executed": False,
        },
        "runs": runs,
        "inventory_finding": {
            "exact_retained_git_checkpoints_available": len(checkpoint_order),
            "final_worktrees_are_dirty": any(not run["final_worktree"]["status"]["clean"] for run in runs),
            "final_worktrees_require_manifest_identity_not_head": True,
            "p0_identity_precondition_pass": all(record["hashes"] == canonical_p0["hashes"] for record in p0_records)
            and len(set(environment_ids)) == 1,
            "candidate_frontier_admitted": False,
            "next_gate": "isolated offline P0 replay and finite-boundary admission",
        },
        "claim_boundary": "Opened Track A byte/provenance inventory only; no replay, determinism, behavioral divergence, OIA separator, ontology-revision, decision-value, sealed, or Track B claim.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("payload_root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = inventory(args.payload_root.resolve())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
