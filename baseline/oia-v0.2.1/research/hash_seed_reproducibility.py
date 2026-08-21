"""Cross-process reproducibility check for the frozen audit-002 input.

This maintenance check never executes the CPython codec substrate or the opened
``cp437`` target. It only recomputes the OIA report from the already frozen
opaque finite-machine input under multiple interpreter hash seeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "external" / "cpython_codecs" / "audit_002"
DEFAULT_SEEDS = (0, 1, 2, 5, 10, 42, 123)
EXPECTED_REPORT_SHA256 = "10bbdb8151be0b073a76a2faa4cdb8083a992aed3820977c17193a40fbe5f2ce"
EXPECTED_POLICY_SHA256 = "612c0572b8f04a4fd3ff82ef2f33f198cda6442200ca7876f24deb6cd3918799"
TIE_BRANCH_OUTPUT = "o_a4a07edff17329dd"
EXPECTED_TIE_ACTION = "a_4763bdccab175d30"


def serialized_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def worker_result() -> dict[str, object]:
    sys.path.insert(0, str(ROOT / "src"))
    from ontology_auditor.io import audit_payload

    audit_input = json.loads(
        (AUDIT_DIR / "audit_input.opaque.json").read_text(encoding="utf-8")
    )
    report = audit_payload(audit_input)
    identity = report["full_candidate_identification"]["adaptive"]
    if not isinstance(identity, Mapping):
        raise TypeError("unexpected adaptive identity result")
    policy = identity.get("policy")
    if not isinstance(policy, Mapping):
        raise TypeError("adaptive identity result has no serialized policy")
    branches = policy.get("branches")
    if not isinstance(branches, Mapping):
        raise TypeError("adaptive identity policy has no root branches")
    tie_node = branches.get(TIE_BRANCH_OUTPUT)
    if not isinstance(tie_node, Mapping):
        raise TypeError(f"missing frozen tie branch {TIE_BRANCH_OUTPUT}")

    return {
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "report_sha256": sha256_bytes(serialized_bytes(report)),
        "policy_sha256": sha256_bytes(serialized_bytes(policy)),
        "tie_branch_action": tie_node.get("action"),
        "root_action": policy.get("action"),
        "worst_case_steps": identity.get("worst_case_steps"),
        "exact": identity.get("exact"),
    }


def run_regression(seeds: Sequence[int] = DEFAULT_SEEDS) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for seed in seeds:
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = str(seed)
        env["PYTHONPATH"] = str(ROOT / "src")
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        row = json.loads(completed.stdout)
        if not isinstance(row, dict):
            raise TypeError("hash-seed worker did not return an object")
        rows.append(row)

    report_hashes = sorted({str(row["report_sha256"]) for row in rows})
    policy_hashes = sorted({str(row["policy_sha256"]) for row in rows})
    tie_actions = sorted({str(row["tie_branch_action"]) for row in rows})
    result: dict[str, object] = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-002",
        "maintenance_release": "0.2.1",
        "scope": (
            "recompute the frozen opaque audit input only; no codec substrate or "
            "cp437 outcome execution"
        ),
        "serialization": "UTF-8 json.dumps(indent=2, sort_keys=True) plus newline",
        "seeds": [int(seed) for seed in seeds],
        "expected_historical_report_sha256": EXPECTED_REPORT_SHA256,
        "expected_historical_policy_sha256": EXPECTED_POLICY_SHA256,
        "expected_tie_branch_action": EXPECTED_TIE_ACTION,
        "unique_report_sha256": report_hashes,
        "unique_policy_sha256": policy_hashes,
        "unique_tie_branch_actions": tie_actions,
        "single_report_hash": len(report_hashes) == 1,
        "single_policy_hash": len(policy_hashes) == 1,
        "single_tie_action": len(tie_actions) == 1,
        "matches_historical_report": report_hashes == [EXPECTED_REPORT_SHA256],
        "matches_historical_policy": policy_hashes == [EXPECTED_POLICY_SHA256],
        "matches_canonical_tie_action": tie_actions == [EXPECTED_TIE_ACTION],
        "rows": rows,
    }
    result["pass"] = all(
        bool(result[key])
        for key in (
            "single_report_hash",
            "single_policy_hash",
            "single_tie_action",
            "matches_historical_report",
            "matches_historical_policy",
            "matches_canonical_tie_action",
        )
    )
    return result


def validate_result(result: Mapping[str, Any]) -> None:
    if not result.get("pass"):
        raise AssertionError(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        help="write deterministic structural evidence to this path",
    )
    args = parser.parse_args()

    if args.worker:
        print(json.dumps(worker_result(), sort_keys=True))
        return

    result = run_regression()
    validate_result(result)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"wrote {output}")
    print(rendered, end="")


if __name__ == "__main__":
    main()
