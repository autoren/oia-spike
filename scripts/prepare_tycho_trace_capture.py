#!/usr/bin/env python3
"""Verify or apply the logging-only Tycho trace-capture patch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "integrations/tycho/trace-capture-v0.1.patch"
EXPECTED_PATCH_SHA256 = "804db588cce430242035c1d26e4f8f19bc214a3cacdfae277153dbeac5cdc27c"
EXPECTED_COMMIT = "f68912a764372ead0a610db2e1c011d41ce5197e"
EXPECTED_TREE = "d5ff6a4e142934ceb865e403e3aa92d80bfa245c"
EXPECTED_CHANGED_PATHS = {
    "tests/harness/test_action_availability.py",
    "tycho/harness/harness.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def prepare(repo: Path, *, apply: bool = False) -> dict:
    repo = repo.resolve()
    if sha256(PATCH) != EXPECTED_PATCH_SHA256:
        raise ValueError("Tycho trace-capture patch hash changed")
    commit = git_output(repo, "rev-parse", "HEAD^{commit}")
    tree = git_output(repo, "rev-parse", "HEAD^{tree}")
    if commit != EXPECTED_COMMIT or tree != EXPECTED_TREE:
        raise ValueError(f"Tycho source pin mismatch: commit={commit} tree={tree}")
    if git_output(repo, "status", "--porcelain"):
        raise ValueError("Tycho source worktree must be clean before patch preparation")
    subprocess.run(
        ["git", "-C", str(repo), "apply", "--check", str(PATCH)],
        check=True,
    )
    if apply:
        subprocess.run(
            ["git", "-C", str(repo), "apply", str(PATCH)],
            check=True,
        )
        changed = set(git_output(repo, "diff", "--name-only").splitlines())
        if changed != EXPECTED_CHANGED_PATHS:
            raise ValueError(f"Tycho patch changed unexpected paths: {sorted(changed)}")
        subprocess.run(
            ["git", "-C", str(repo), "diff", "--check"],
            check=True,
        )
        status = "logging_patch_applied"
    else:
        changed = set()
        status = "logging_patch_applicable"
    return {
        "status": status,
        "source_commit": commit,
        "source_tree": tree,
        "patch_sha256": EXPECTED_PATCH_SHA256,
        "changed_paths": sorted(changed),
        "model_calls": 0,
        "environment_actions": 0,
        "project_reopening_effect": "none",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = prepare(args.repo, apply=args.apply)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["status"])


if __name__ == "__main__":
    main()
