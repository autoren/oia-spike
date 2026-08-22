#!/usr/bin/env python3
"""Verify freezes whose manifests historically pinned the mutable root README.

The original manifests and verifiers remain unchanged. Each manifest correctly
describes its pinned pre-outcome Git snapshot, but its root ``README.md`` entry
is a repository index rather than experiment-local evidence. This maintenance
verifier reconstructs and runs every original verifier at its exact historical
snapshot, then checks present-day byte continuity for every manifest entry
except that one explicitly mutable index.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MUTABLE_INDEX_PATHS = frozenset({"README.md"})
MAINTENANCE_RECORD = ROOT / "audits" / "FREEZE_VERIFIER_MAINTENANCE.json"


@dataclass(frozen=True)
class Freeze:
    audit_id: str
    snapshot: str
    manifest: str
    manifest_sha256: str
    verifier: str
    support_paths: frozenset[str] = frozenset()
    forbidden_current_paths: frozenset[str] = frozenset()


FREEZES = (
    Freeze(
        audit_id="OIA-1-TRACK-A-005e",
        snapshot="aba0fab0a5d8da66eaf784cd2d8f9d13bec51de6",
        manifest="audits/track-a-005e/LOCAL_OUTCOME_FREEZE_SHA256SUMS.txt",
        manifest_sha256="5d85f88e854f4d07ed94b95c41848927830316cef8edef08c71c6af48137e8e6",
        verifier="scripts/verify_track_a_005e_freeze.py",
        support_paths=frozenset(
            {
                "audits/track-a-005c/behavior-outcome/ADMISSION_AND_OIA_RESULT.json",
                "audits/track-a-005d/step2-outcome/STEP2_ARCHIVE_OUTCOME_RESULT.json",
            }
        ),
        forbidden_current_paths=frozenset({"audits/track-a-005e/outcome"}),
    ),
    Freeze(
        audit_id="OIA-1-TRACK-A-006a",
        snapshot="1eaa085def449312fb75fc9504b6a3bf500776b2",
        manifest="audits/track-a-006a/CONTROLLED_OPEN_WORLD_FREEZE_SHA256SUMS.txt",
        manifest_sha256="3b19a29569c01b20d1082fc2e6891b1afd8f49c3bd412d6e836599245a5859ea",
        verifier="scripts/verify_track_a_006a_freeze.py",
        support_paths=frozenset(
            {
                "baseline/oia-v0.2.1/src/ontology_auditor/__init__.py",
                "baseline/oia-v0.2.1/src/ontology_auditor/model.py",
                "baseline/oia-v0.2.1/src/ontology_auditor/synthesis.py",
            }
        ),
    ),
    Freeze(
        audit_id="OIA-1-TRACK-A-006b",
        snapshot="057a152915fa52c67c897a8d24394d4f51b0eddf",
        manifest="audits/track-a-006b/REJECT_AWARE_FREEZE_SHA256SUMS.txt",
        manifest_sha256="6908566370cb4d1546140614dc95dea7f79ef67abf0f1f3bb59e09e40a2e5043",
        verifier="scripts/verify_track_a_006b_freeze.py",
        support_paths=frozenset({"scripts/run_track_a_006a_controlled_open_world.py"}),
    ),
    Freeze(
        audit_id="OIA-1-TRACK-A-006c",
        snapshot="a8f3d84ad45bf84622bf703bfa7d80923559652b",
        manifest="audits/track-a-006c/SEQUENTIAL_FUSION_FREEZE_SHA256SUMS.txt",
        manifest_sha256="295056f7783a4f8c2a2696d3072a10f93b9c69b7aaac611d8a4e517b621ec0e7",
        verifier="scripts/verify_track_a_006c_freeze.py",
        support_paths=frozenset({"scripts/run_track_a_006b_reject_aware.py"}),
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
    ).stdout


def read_manifest(freeze: Freeze) -> dict[str, str]:
    path = ROOT / freeze.manifest
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{freeze.audit_id} manifest missing or symlinked")
    if sha256(path) != freeze.manifest_sha256:
        raise ValueError(f"{freeze.audit_id} historical manifest changed")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if relative in entries:
            raise ValueError(f"{freeze.audit_id} duplicate freeze path: {relative}")
        entries[relative] = digest
    if not entries or not MUTABLE_INDEX_PATHS < entries.keys():
        raise ValueError(f"{freeze.audit_id} mutable-index path set changed")
    return entries


def verify_maintenance_record() -> None:
    record = json.loads(MAINTENANCE_RECORD.read_text(encoding="utf-8"))
    expected = [
        {
            "audit_id": freeze.audit_id,
            "historical_manifest_sha256": freeze.manifest_sha256,
            "historical_snapshot_commit": freeze.snapshot,
        }
        for freeze in FREEZES
    ]
    if record["schema_version"] != 1 or record["repair"]["freezes"] != expected:
        raise ValueError("historical freeze maintenance provenance changed")
    if record["repair"]["explicit_mutable_index_exemptions"] != sorted(
        MUTABLE_INDEX_PATHS
    ):
        raise ValueError("historical freeze mutable-index exemptions changed")
    boundary = record["empirical_boundary"]
    if (
        boundary["candidate_frontiers_changed"]
        or boundary["frozen_protocols_changed"]
        or boundary["game_source_executions"] != 0
        or boundary["oia_actions_changed"]
        or boundary["outcomes_created_or_rerun"]
        or boundary["real_arc_actions"] != 0
        or boundary["resets"] != 0
    ):
        raise ValueError("historical freeze maintenance crossed an empirical boundary")


def verify_historical_snapshot(
    freeze: Freeze, entries: dict[str, str]
) -> dict[str, object]:
    resolved = git_bytes("rev-parse", f"{freeze.snapshot}^{{commit}}").decode().strip()
    if resolved != freeze.snapshot:
        raise ValueError(f"{freeze.audit_id} historical snapshot did not resolve exactly")
    subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", freeze.snapshot, "HEAD"],
        check=True,
        capture_output=True,
    )
    historical_manifest = git_bytes("show", f"{freeze.snapshot}:{freeze.manifest}")
    if sha256_bytes(historical_manifest) != freeze.manifest_sha256:
        raise ValueError(f"{freeze.audit_id} historical manifest snapshot mismatch")
    for relative, expected in entries.items():
        observed = sha256_bytes(git_bytes("show", f"{freeze.snapshot}:{relative}"))
        if observed != expected:
            raise ValueError(f"{freeze.audit_id} historical snapshot mismatch: {relative}")

    with tempfile.TemporaryDirectory(prefix="oia-historical-freeze-") as temporary:
        snapshot = Path(temporary)
        required = set(entries) | set(freeze.support_paths) | {freeze.manifest}
        for relative in required:
            destination = snapshot / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(git_bytes("show", f"{freeze.snapshot}:{relative}"))
        verifier = subprocess.run(
            [sys.executable, freeze.verifier],
            cwd=snapshot,
            check=True,
            capture_output=True,
            text=True,
        )
    lines = [line for line in verifier.stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"{freeze.audit_id} historical verifier produced no result")
    result = json.loads(lines[-1])
    if result.get("pass") is not True:
        raise ValueError(f"{freeze.audit_id} historical verifier did not pass")
    return result


def verify_current_continuity(freeze: Freeze, entries: dict[str, str]) -> None:
    for relative, expected in entries.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"{freeze.audit_id} current path missing or symlinked: {relative}")
        if relative not in MUTABLE_INDEX_PATHS and sha256(path) != expected:
            raise ValueError(f"{freeze.audit_id} current frozen artifact changed: {relative}")
    for relative in freeze.forbidden_current_paths:
        if (ROOT / relative).exists():
            raise ValueError(f"{freeze.audit_id} forbidden pre-action path exists: {relative}")


def verify_freeze(freeze: Freeze) -> dict[str, object]:
    entries = read_manifest(freeze)
    historical = verify_historical_snapshot(freeze, entries)
    verify_current_continuity(freeze, entries)
    return {
        "audit_id": freeze.audit_id,
        "current_frozen_entries_verified": len(entries) - len(MUTABLE_INDEX_PATHS),
        "historical_manifest_entries_verified": len(entries),
        "historical_snapshot": freeze.snapshot,
        "historical_verifier": historical,
        "mutable_index_exemptions": sorted(MUTABLE_INDEX_PATHS),
        "pass": True,
    }


def main() -> None:
    verify_maintenance_record()
    results = [verify_freeze(freeze) for freeze in FREEZES]
    print(
        json.dumps(
            {
                "freeze_count": len(results),
                "pass": True,
                "results": results,
                "status": "historical_freezes_and_current_continuity_verified",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
