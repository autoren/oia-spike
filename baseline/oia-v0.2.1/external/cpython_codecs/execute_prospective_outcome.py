"""Execute the frozen OIA policy once on the predeclared opened target."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from codec_adapter import HORIZON, initial_state_key, output_id, source_step
from ontology_auditor import PolicyNode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT_DIR = HERE / "audit_002"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(name: str) -> None:
    for raw_line in (AUDIT_DIR / name).read_text(encoding="utf-8").splitlines():
        digest, relative = raw_line.split("  ", 1)
        actual = sha256(AUDIT_DIR / relative)
        if actual != digest:
            raise RuntimeError(f"pre-outcome checksum mismatch for {relative}")


def load_json(name: str) -> object:
    return json.loads((AUDIT_DIR / name).read_text(encoding="utf-8"))


def write_json(name: str, payload: object) -> None:
    (AUDIT_DIR / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )




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
        actual = sha256(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"instrument source checksum mismatch for {relative}")


def main() -> None:
    verify_manifest("PRE_OUTCOME_SHA256SUMS")
    verify_instrument_sources()
    report = load_json("oia_report.json")
    encoder = load_json("encoder_manifest.opened.json")
    protocol = load_json("audit_protocol.frozen.json")
    if not isinstance(report, Mapping) or not isinstance(encoder, Mapping) or not isinstance(protocol, Mapping):
        raise TypeError("invalid frozen artifacts")

    raw_policy = report["full_candidate_identification"]["adaptive"]["policy"]
    if not isinstance(raw_policy, Mapping):
        raise RuntimeError("no primary policy to execute")
    policy = PolicyNode.from_dict(raw_policy)
    target = encoder["prospective_target"]
    actions = encoder["actions"]
    if not isinstance(target, Mapping) or not isinstance(actions, Mapping):
        raise TypeError("invalid encoder manifest")
    codec_name = str(target["codec"])
    state = initial_state_key(codec_name)
    node = policy
    trace: list[dict[str, object]] = []
    status = "resolved_inside_candidate_set"
    leaf_candidates: list[str] | None = None

    while not node.is_leaf:
        action_id = str(node.action)
        action = actions[action_id]
        if not isinstance(action, Mapping):
            raise TypeError("invalid action specification")
        token, state = source_step(codec_name, state, action, horizon=HORIZON)
        encoded = output_id(token)
        available = sorted(node.branches)
        trace.append(
            {
                "step": len(trace) + 1,
                "opaque_action": action_id,
                "opened_action": dict(action),
                "opaque_observation": encoded,
                "opened_observation": token,
                "candidate_branch_observations": available,
                "branch_present": encoded in node.branches,
            }
        )
        if encoded not in node.branches:
            status = "outside_model"
            break
        node = node.branches[encoded]

    if status != "outside_model":
        leaf_candidates = list(node.candidates)

    outcome = {
        "audit_id": protocol["audit_id"],
        "pre_outcome_manifest_verified": True,
        "target_id": target["target_id"],
        "opened_target_codec": codec_name,
        "target_was_frozen_outside_candidate_set": True,
        "primary_policy_status": report["full_candidate_identification"]["adaptive"]["status"],
        "primary_policy_exact": report["full_candidate_identification"]["adaptive"]["exact"],
        "outcome_status": status,
        "steps_executed": len(trace),
        "leaf_candidates": leaf_candidates,
        "trace": trace,
        "post_outcome_policy_changes": 0,
        "interpretation": (
            "the first prospective observation was absent from every branch of "
            "the frozen candidate policy" if status == "outside_model" else
            "the outside target remained behaviorally covered by a candidate leaf on this policy"
        ),
    }
    write_json("prospective_outcome.json", outcome)

    final_files = [
        path for path in AUDIT_DIR.iterdir()
        if path.is_file() and path.name != "FINAL_SHA256SUMS"
    ]
    (AUDIT_DIR / "FINAL_SHA256SUMS").write_text(
        "\n".join(
            f"{sha256(path)}  {path.name}" for path in sorted(final_files)
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(outcome, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
