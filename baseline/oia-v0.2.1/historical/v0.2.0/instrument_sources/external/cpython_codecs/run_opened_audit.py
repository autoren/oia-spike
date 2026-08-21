"""Run frozen Track-A audit 002 without executing the prospective target."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Mapping

from codec_adapter import (
    HORIZON,
    initial_state_key,
    output_id,
    source_step,
)
from ontology_auditor import (
    CandidateSystem,
    PolicyNode,
    label_terminal,
    verify_serialized_adaptive_result,
)
from ontology_auditor.io import audit_payload

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT_DIR = HERE / "audit_002"


def load_json(name: str) -> object:
    return json.loads((AUDIT_DIR / name).read_text(encoding="utf-8"))


def write_json(name: str, payload: object) -> None:
    (AUDIT_DIR / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(name: str) -> None:
    for raw_line in (AUDIT_DIR / name).read_text(encoding="utf-8").splitlines():
        digest, relative = raw_line.split("  ", 1)
        path = AUDIT_DIR / relative
        actual = sha256(path)
        if actual != digest:
            raise RuntimeError(f"checksum mismatch for {relative}: {actual} != {digest}")




def verify_instrument_sources() -> None:
    payload = load_json("instrument_source_provenance.json")
    if not isinstance(payload, Mapping):
        raise TypeError("instrument source provenance must be an object")
    records = payload.get("files")
    if not isinstance(records, list):
        raise TypeError("instrument source provenance files must be a list")
    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError("instrument source record must be an object")
        relative = str(record["path"])
        expected = str(record["sha256"])
        path = ROOT / relative
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"instrument source checksum mismatch for {relative}: "
                f"{actual} != {expected}"
            )


def blackbox_replay(
    policy_payload: Mapping[str, object],
    encoder: Mapping[str, object],
) -> dict[str, object]:
    actions = encoder["actions"]
    candidates = encoder["candidates"]
    if not isinstance(actions, Mapping) or not isinstance(candidates, Mapping):
        raise TypeError("invalid encoder manifest")
    policy = PolicyNode.from_dict(policy_payload)
    rows: list[dict[str, object]] = []

    for candidate, codec_name_raw in sorted(candidates.items()):
        codec_name = str(codec_name_raw)
        state = initial_state_key(codec_name)
        node = policy
        trace: list[dict[str, object]] = []
        while not node.is_leaf:
            action_id = str(node.action)
            action = actions[action_id]
            if not isinstance(action, Mapping):
                raise TypeError("invalid action specification")
            token, state = source_step(codec_name, state, action, horizon=HORIZON)
            encoded = output_id(token)
            trace.append({"action": action_id, "output": encoded})
            if encoded not in node.branches:
                raise AssertionError(
                    f"black-box replay produced missing branch for {candidate}"
                )
            node = node.branches[encoded]
        if candidate not in node.candidates:
            raise AssertionError(
                f"black-box replay ended at leaf excluding {candidate}"
            )
        rows.append(
            {
                "candidate_id": candidate,
                "steps": len(trace),
                "leaf_candidates": list(node.candidates),
                "opaque_trace": trace,
                "result": "pass",
            }
        )

    return {
        "baseline": "reset_and_query_direct_codec_oracle_policy_replay",
        "uses_compiled_candidate_states": False,
        "selection_role": "none; this baseline verifies behavioral adequacy of the selected policy only",
        "comparative_superiority_claim": False,
        "candidate_count": len(rows),
        "maximum_steps": max(int(row["steps"]) for row in rows),
        "all_paths_valid": True,
        "rows": rows,
    }


def main() -> None:
    verify_manifest("FREEZE_SHA256SUMS")
    verify_instrument_sources()
    payload = load_json("audit_input.opaque.json")
    if not isinstance(payload, Mapping):
        raise TypeError("audit input must be an object")

    start = time.perf_counter()
    report = audit_payload(payload)
    elapsed = time.perf_counter() - start
    write_json("oia_report.json", report)

    system = CandidateSystem.from_dict(payload)
    identity = report["full_candidate_identification"]["adaptive"]
    target = report["target_class_identification"]["adaptive"]
    decision = report["decision_relevance"]["minimum_probe_to_common_optimum"]["adaptive"]
    if not isinstance(identity, Mapping) or not isinstance(target, Mapping) or not isinstance(decision, Mapping):
        raise TypeError("unexpected OIA report schema")
    identity_depth = verify_serialized_adaptive_result(system, identity)
    target_depth = verify_serialized_adaptive_result(
        system, target, label_terminal(payload["labels"])
    )
    # The decision target has the same partition as the frozen label target in
    # this audit, so its executable witness is independently checked under the
    # same terminal predicate.
    decision_depth = verify_serialized_adaptive_result(
        system, decision, label_terminal(payload["labels"])
    )

    policy_payload = identity.get("policy")
    if not isinstance(policy_payload, Mapping):
        raise RuntimeError("primary OIA result did not provide a policy")
    encoder = load_json("encoder_manifest.opened.json")
    if not isinstance(encoder, Mapping):
        raise TypeError("encoder manifest must be an object")
    blackbox = blackbox_replay(policy_payload, encoder)
    write_json("blackbox_comparison.json", blackbox)

    selection = {
        "audit_id": "OIA-1-TRACK-A-002",
        "freeze_manifest_verified": True,
        "prospective_target_not_executed": True,
        "primary_endpoint": "full_candidate_identification.adaptive",
        "status": identity["status"],
        "exact": identity["exact"],
        "enumeration_complete": identity["enumeration_complete"],
        "optimality_certified": identity["optimality_certified"],
        "depth_claim": identity["depth_claim"],
        "verified_worst_case_steps": identity_depth,
        "reachable_beliefs": identity["reachable_beliefs"],
        "root_action": policy_payload["action"],
        "secondary_target_verified_steps": target_depth,
        "decision_verified_steps": decision_depth,
        "identity_minus_decision_worst_case_steps": (
            int(identity_depth or 0) - int(decision_depth or 0)
        ),
        "blackbox_replay_all_paths_valid": blackbox["all_paths_valid"],
        "blackbox_maximum_steps": blackbox["maximum_steps"],
        "local_runtime_seconds_console_only": None,
        "outcome_execution_authorized": True,
    }
    write_json("selection_record.pre_outcome.json", selection)

    pre_outcome_files = [
        path
        for path in AUDIT_DIR.iterdir()
        if path.is_file()
        and path.name not in {
            "PRE_OUTCOME_SHA256SUMS",
            "prospective_outcome.json",
            "FINAL_SHA256SUMS",
            "execution_transcript.txt",
        }
    ]
    lines = [
        f"{sha256(path)}  {path.name}" for path in sorted(pre_outcome_files)
    ]
    (AUDIT_DIR / "PRE_OUTCOME_SHA256SUMS").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(json.dumps(selection, indent=2, sort_keys=True))
    print(f"TIMING_LOCAL oia_audit_seconds={elapsed:.9f}")
    print("prospective target has not been executed")


if __name__ == "__main__":
    main()
