#!/usr/bin/env python3
"""Verify the frozen Track A 004a adapter and pre-run package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-004a"
EXPECTED_SOURCE_SHA256 = "d11529d4281746d4a2d89d075d23ac1bbdc12d4deb3c2de2dc9c10de18bec039"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(name: str) -> object:
    return json.loads((AUDIT_ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    manifest_entries = 0
    for line in (AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
            raise ValueError(f"pre-run checksum mismatch: {relative}")
        manifest_entries += 1

    source = load_json("ADAPTER_SOURCE_TRACES.json")
    if source["source"]["sha256"] != EXPECTED_SOURCE_SHA256:
        raise ValueError("source evidence pin changed")
    for candidate in source["candidates"]:
        if len(candidate["word_records"]) != 84:
            raise ValueError("source trace coverage changed")
        for record in candidate["word_records"]:
            reconstructed = dict(record["trace"])
            reconstructed["p0"] = source["common_p0"]
            if sha256_bytes(canonical_bytes(reconstructed)) != record["source_trace_sha256"]:
                raise ValueError("distilled source trace does not match its original hash")

    sys.path.insert(0, str(ROOT / "scripts"))
    import prepare_track_a_004a as prepare

    rebuilt_input, rebuilt_outputs, rebuilt_states, rebuilt_validation = prepare.build_adapter(source)
    if rebuilt_input != load_json("OIA_INPUT.frozen.json"):
        raise ValueError("frozen OIA input is not reproducible")
    if {"audit_id": prepare.AUDIT_ID, "outputs": rebuilt_outputs} != load_json(
        "OUTPUT_MANIFEST.opened.json"
    ):
        raise ValueError("output manifest is not reproducible")
    if rebuilt_states != load_json("STATE_MANIFEST.opened.json"):
        raise ValueError("state manifest is not reproducible")
    preserved = load_json("TRACE_PRESERVATION.json")
    if preserved["adapter_validation"] != rebuilt_validation or preserved["result"] != "pass":
        raise ValueError("trace-preservation validation changed")

    provenance = load_json("INSTRUMENT_SOURCE_PROVENANCE.json")
    if provenance["accepted_baseline"] != "OIA-1 v0.2.1":
        raise ValueError("accepted OIA baseline changed")
    for record in provenance["files"]:
        path = ROOT / record["path"]
        if path.stat().st_size != record["size_bytes"] or sha256_file(path) != record["sha256"]:
            raise ValueError(f"instrument source mismatch: {record['path']}")

    protocol = load_json("RETROSPECTIVE_PROTOCOL.frozen.json")
    if protocol["status_at_freeze"] != "frozen_before_full_track_a_004a_audit_execution":
        raise ValueError("protocol freeze status changed")
    if protocol["epistemic_ordering"]["prospective_separator_discovery_claim_allowed"] is not False:
        raise ValueError("retrospective claim boundary changed")
    if protocol["intervention_boundary"]["real_arc_actions_authorized"] is not False:
        raise ValueError("ARC action boundary changed")
    precheck = load_json("ENGINEERING_PRECHECK.pre-full-audit.json")
    if precheck["full_audit_executed"] is not False:
        raise ValueError("precheck boundary changed")
    if precheck["observed_result"]["sequence"] != ["ACTION2"]:
        raise ValueError("preserved precheck result changed")

    baseline_src = ROOT / "baseline" / "oia-v0.2.1" / "src"
    sys.path.insert(0, str(baseline_src))
    from ontology_auditor import CandidateSystem

    system = CandidateSystem.from_dict(rebuilt_input)
    if tuple(system.machines) != ("C0001", "C0002") or system.actions != prepare.ACTIONS:
        raise ValueError("frozen candidate interface changed")
    if any(len(machine.states) != 86 for machine in system.machines.values()):
        raise ValueError("compiled machine state count changed")

    print(
        json.dumps(
            {
                "audit_id": prepare.AUDIT_ID,
                "candidate_count": len(system.machines),
                "manifest_entries": manifest_entries,
                "pass": True,
                "source_words": sum(len(item["word_records"]) for item in source["candidates"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
