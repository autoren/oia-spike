#!/usr/bin/env python3
"""Verify the compact Track A 003b candidate-admission outcome package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
OUTCOME_ROOT = ROOT / "audits" / "track-a-003b" / "outcome"
MANIFEST_PATH = OUTCOME_ROOT / "PACKAGE_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_outcome_file(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe outcome path: {relative!r}")
    path = OUTCOME_ROOT.joinpath(*pure.parts)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"outcome entry is not a regular file: {relative!r}")
    return path


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["gate_verdict"] != "candidate_frontier_feasible":
        raise ValueError("unexpected package verdict")
    hashes: dict[str, str] = {}
    for entry in manifest["files"]:
        path = safe_outcome_file(entry["path"])
        if path.stat().st_size != entry["size_bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"outcome file mismatch: {entry['path']}")
        hashes[entry["path"]] = entry["sha256"]

    checksums: dict[str, str] = {}
    for line in safe_outcome_file("SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        if sha256(safe_outcome_file(relative)) != digest:
            raise ValueError(f"checksum mismatch: {relative}")
        checksums[relative] = digest
    if set(checksums) != {"ADMISSION_SUMMARY.json", "TRACK_A_003B_REPORT.md"}:
        raise ValueError("outcome checksum coverage changed")

    generator = manifest["independent_summarizer"]
    generator_path = (ROOT / generator["path"]).resolve()
    if ROOT not in generator_path.parents or sha256(generator_path) != generator["sha256"]:
        raise ValueError("independent summarizer pin mismatch")

    summary = json.loads(safe_outcome_file("ADMISSION_SUMMARY.json").read_text(encoding="utf-8"))
    if summary["status"] != "complete" or summary["gate_verdict"] != "candidate_frontier_feasible":
        raise ValueError("summary status or verdict changed")
    expected_raw = {
        "p0_results": "100fd65cf2bbd7bb314f98c6d918dfa04140a8380f6ad32f4807ac5ecd74a260",
        "provisional_results": "e68b0d13663cf91d06fd2d2bcb5edb2e83b668049c2e23e127bfd8258a09ed2a",
        "full_results": "d11529d4281746d4a2d89d075d23ac1bbdc12d4deb3c2de2dc9c10de18bec039",
    }
    if {name: record["sha256"] for name, record in summary["raw_evidence"].items()} != expected_raw:
        raise ValueError("raw evidence hashes changed")

    result = summary["result"]
    if result["admitted_candidates"] != ["max/final", "max/iteration_2"]:
        raise ValueError("admitted candidates changed")
    if result["source_records_screened"] != 13 or result["behavioral_duplicate_count"] != 11:
        raise ValueError("candidate accounting changed")
    if result["nondeterministic_word_count"] != 0 or not result["all_promoted_words_deterministic"]:
        raise ValueError("determinism result changed")
    divergence = result["first_divergence"]
    if divergence["word"] != ["ACTION2"] or divergence["word_index"] != 1:
        raise ValueError("first divergence changed")

    accounting = summary["execution_accounting"]
    if accounting["fresh_candidate_processes_total"] != 2449 or accounting["predicted_transition_steps"] != 6612:
        raise ValueError("execution accounting changed")
    for field in (
        "real_arc_actions",
        "network_or_service_calls",
        "credential_uses",
        "model_or_api_calls",
        "oia_separator_runs",
    ):
        if accounting[field] != 0:
            raise ValueError(f"claim boundary crossed: {field}")
    integrity = summary["integrity"]
    expected_integrity = {
        "all_candidate_bundles_hash_verified": True,
        "all_full_repetitions_pass": True,
        "all_p0_replays_exact": True,
        "all_provisional_results_pass": True,
        "candidate_or_p0_output_emitted_during_p0": False,
        "full_and_provisional_signatures_match": True,
        "network_disabled": True,
        "session_and_post_p0_state_excluded": True,
        "unexpected_candidate_or_p0_file_access_during_p0": False,
    }
    if integrity != expected_integrity:
        raise ValueError("integrity record changed")

    print(
        json.dumps(
            {
                "admitted_candidates": result["admitted_candidates"],
                "audit_id": summary["audit_id"],
                "gate_verdict": summary["gate_verdict"],
                "manifest_entries": len(hashes),
                "pass": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
