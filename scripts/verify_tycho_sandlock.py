#!/usr/bin/env python3
"""Verify the frozen Tycho Sandlock R1 evidence and claim boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "integrations" / "tycho-sandlock"
PROTOCOL = BASE / "SANDBOX_PROTOCOL.json"
FREEZE = BASE / "SANDBOX_IMPLEMENTATION_FREEZE.json"
PATCH = BASE / "sandlock-python-sandbox-v0.1.patch"
LIVE = BASE / "LIVE_PROBE_RESULT.json"
RESULT = BASE / "SANDBOX_RESULT.json"
PROBE = ROOT / "scripts" / "qualify_tycho_sandlock.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(path: Path = PROTOCOL) -> dict:
    payload = load(path)
    if payload["schema_version"] != "OIA-TYCHO-SANDLOCK-PROTOCOL-0.1":
        raise ValueError("protocol schema changed")
    execution = payload["authorized_post_freeze_execution"]
    expected_positive = {
        "sandlock_feature_checks": 1,
        "functional_isolation_probes": 1,
        "unsandboxed_network_controls": 1,
        "timeout_limit_probes": 1,
        "memory_limit_probes": 1,
        "patch_application_checks": 1,
        "patched_tycho_sandbox_unit_suites": 1,
    }
    if {key: execution.get(key) for key in expected_positive} != expected_positive:
        raise ValueError("bounded execution allowance changed")
    expected_zero = {
        "model_loads",
        "model_calls",
        "gpu_runs",
        "arc_environment_actions",
        "kaggle_runs_or_uploads",
        "oia_runs",
    }
    if any(execution.get(key) != 0 for key in expected_zero):
        raise ValueError("forbidden execution boundary changed")
    if payload["sandbox_policy_contract"]["forbidden_substitute"] != (
        "TYCHO_SANDBOX_RUNTIME=host"
    ):
        raise ValueError("host fallback boundary changed")
    return payload


def validate_freeze(path: Path = FREEZE) -> dict:
    payload = load(path)
    if payload["tycho_source"]["commit"] != (
        "f68912a764372ead0a610db2e1c011d41ce5197e"
    ):
        raise ValueError("Tycho source pin changed")
    expected = {
        PROTOCOL: payload["protocol"]["sha256"],
        PATCH: payload["patch"]["sha256"],
        PROBE: payload["live_probe"]["sha256"],
    }
    for artifact, digest in expected.items():
        if sha256(artifact) != digest:
            raise ValueError(f"frozen artifact hash changed: {artifact.name}")
    patch_text = PATCH.read_text(encoding="utf-8")
    changed = sorted(
        set(re.findall(r"^diff --git a/(.+?) b/", patch_text, flags=re.MULTILINE))
    )
    permitted = sorted(payload["patch"]["permitted_source_files"])
    if changed != permitted:
        raise ValueError("patch source-file scope changed")
    required_tokens = {
        'RUNTIMES = (*CONTAINER_RUNTIMES, "sandlock")',
        'candidates = ("finch", "docker") if sys.platform == "darwin" else CONTAINER_RUNTIMES',
        '"--net-deny",',
        '"--max-processes",',
        '"--clean-env",',
        'if self.runtime == "sandlock" and process.returncode == 124:',
    }
    if any(token not in patch_text for token in required_tokens):
        raise ValueError("patch isolation contract changed")
    return payload


def validate_live(path: Path = LIVE) -> dict:
    payload = load(path)
    if payload["runtime_resolution"] != "sandlock":
        raise ValueError("live runtime changed")
    if payload["sandlock_binary_sha256"] != (
        "346cd6c5c7773384f9803794a3ab6946aeb7f05e1d272c9d6fb7e01a2b4b5c98"
    ):
        raise ValueError("live Sandlock binary changed")
    if payload["unsandboxed_control"] != {"tcp": True, "udp": True}:
        raise ValueError("network control did not establish reachability")
    attempts = {item["name"]: item["allowed"] for item in payload["attempts"]}
    expected = {
        "workspace_read": True,
        "workspace_write": True,
        "sibling_sentinel_read": False,
        "host_etc_passwd_read": False,
        "host_users_read": False,
        "outside_write": False,
        "tcp_connect": False,
        "udp_send": False,
        "subprocess_spawn": False,
    }
    if attempts != expected:
        raise ValueError("live capability result changed")
    if payload["grid_result"] != [[6, 3, 0], [7, 4, 1], [8, 5, 2]]:
        raise ValueError("representative grid result changed")
    if payload["functional_returncode"] != 0 or payload["functional_timed_out"]:
        raise ValueError("functional probe did not complete")
    if payload["timeout_probe"] != {
        "returncode": -1,
        "timed_out": True,
        "stderr": "sandlock: timeout after 1s",
    }:
        raise ValueError("timeout mapping changed")
    return payload


def validate_result(path: Path = RESULT) -> dict:
    payload = load(path)
    if payload["verdict"] != (
        "sandlock_adapter_locally_qualified_target_and_throughput_unqualified"
    ):
        raise ValueError("verdict changed")
    accounting = payload["execution_accounting"]
    protocol = validate_protocol()["authorized_post_freeze_execution"]
    for key, expected in protocol.items():
        if accounting.get(key) != expected:
            raise ValueError(f"execution accounting changed: {key}")
    if accounting["unit_tests_collected"] != 14 or accounting["unit_tests_passed"] != 14:
        raise ValueError("patched unit-suite result changed")
    observations = payload["observations"]
    if observations["memory_probe_limit"] != "64M" or observations["memory_probe_exit"] == 0:
        raise ValueError("memory-limit result changed")
    claims = payload["claim_boundary"]
    if not claims["docker_free_mechanism_on_exact_vm"]:
        raise ValueError("local mechanism result changed")
    if not claims["patched_tycho_sandbox_contract_on_exact_vm"]:
        raise ValueError("local adapter result changed")
    forbidden_true = {
        "target_evaluator_kernel_support",
        "x86_64_target_execution",
        "tycho_to_myagent_lifecycle_adapter",
        "model_or_projector_target_gpu_load",
        "nine_hour_throughput",
        "package_ready",
        "arc_correctness_or_progress",
        "oia_discovery_or_transfer",
        "sealed_or_hidden_evaluation",
    }
    if any(claims[key] for key in forbidden_true):
        raise ValueError("claim boundary broadened")
    hashes = payload["artifact_hashes"]
    expected_hashes = {
        "protocol_sha256": sha256(PROTOCOL),
        "implementation_freeze_sha256": sha256(FREEZE),
        "patch_sha256": sha256(PATCH),
        "live_probe_script_sha256": sha256(PROBE),
    }
    if any(hashes[key] != digest for key, digest in expected_hashes.items()):
        raise ValueError("result artifact hash changed")
    return payload


def main() -> None:
    validate_protocol()
    validate_freeze()
    live = validate_live()
    result = validate_result()
    print(
        json.dumps(
            {
                "gate_id": result["gate_id"],
                "runtime": live["runtime_resolution"],
                "status": "verified",
                "verdict": result["verdict"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
