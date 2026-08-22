#!/usr/bin/env python3
"""Compile deterministic Track A 003b traces into a frozen OIA input."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-004a"
BASELINE_ROOT = ROOT / "baseline" / "oia-v0.2.1"
SUMMARY_PATH = ROOT / "audits" / "track-a-003b" / "outcome" / "ADMISSION_SUMMARY.json"
DEFAULT_FULL_RESULTS = ROOT / "local-work" / "track-a-003b" / "admission-results" / "FULL_RESULTS.json"

AUDIT_ID = "OIA-1-TRACK-A-004a"
ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
HORIZON = 3
EXPECTED_FULL_RESULTS_SHA256 = "d11529d4281746d4a2d89d075d23ac1bbdc12d4deb3c2de2dc9c10de18bec039"
EXPECTED_CANDIDATES = ("max/final", "max/iteration_2")
MACHINE_IDS = ("C0001", "C0002")
BOUNDARY_OUTPUT = "OBS_BOUNDARY_EXHAUSTED"

FROZEN_INSTRUMENT_PATHS = (
    "baseline/oia-v0.2.1/SHA256SUMS",
    "baseline/oia-v0.2.1/maintenance/CURRENT_SOURCE_SHA256SUMS",
    "baseline/oia-v0.2.1/maintenance/PROVENANCE_LAYERS.json",
    "baseline/oia-v0.2.1/src/ontology_auditor/__init__.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/audit.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/decision.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/equivalence.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/io.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/model.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/synthesis.py",
    "baseline/oia-v0.2.1/src/ontology_auditor/task_loss.py",
)

PRE_RUN_SOURCE_PATHS = (
    "scripts/prepare_track_a_004a.py",
    "scripts/run_track_a_004a.py",
    "scripts/verify_track_a_004a_prerun.py",
    "scripts/verify_track_a_004a_outcome.py",
    "tests/test_track_a_004a_adapter.py",
)

PRE_RUN_ARTIFACT_NAMES = (
    "ADAPTER_SOURCE_TRACES.json",
    "ENGINEERING_PRECHECK.pre-full-audit.json",
    "INSTRUMENT_SOURCE_PROVENANCE.json",
    "OIA_INPUT.frozen.json",
    "OUTPUT_MANIFEST.opened.json",
    "RETROSPECTIVE_PROTOCOL.frozen.json",
    "STATE_MANIFEST.opened.json",
    "TRACE_PRESERVATION.json",
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def frozen_words() -> list[tuple[str, ...]]:
    return [
        word
        for length in range(1, HORIZON + 1)
        for word in itertools.product(ACTIONS, repeat=length)
    ]


def observed_prefixes() -> list[tuple[str, ...]]:
    return [()] + frozen_words()


def trace_projection(trace: Mapping[str, object]) -> dict[str, object]:
    return {
        key: trace[key]
        for key in ("status", "error_category", "word", "steps")
        if key in trace
    }


def observation_projection(step: Mapping[str, object]) -> dict[str, object]:
    return {
        key: step[key]
        for key in (
            "status",
            "error_category",
            "final_frame_sha256",
            "modeled_progress",
        )
        if key in step
    }


def observation_id(observation: Mapping[str, object]) -> str:
    return "OBS_" + sha256_bytes(canonical_bytes(observation))


def validate_and_distill(full_results: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    stage = full_results.get("stage_result")
    if not isinstance(stage, Mapping) or stage.get("stage") != "full":
        raise ValueError("source is not Track A 003b full-stage evidence")
    if tuple(stage.get("admitted_candidates", ())) != EXPECTED_CANDIDATES:
        raise ValueError("admitted candidate order changed")
    if stage.get("seeds") != [0, 1, 5, 10] or stage.get("repetitions_per_seed") != 2:
        raise ValueError("source seed/repetition matrix changed")

    expected_words = frozen_words()
    results = stage.get("results")
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)):
        raise ValueError("full-stage results must be an array")
    by_candidate = {
        str(item["candidate_id"]): item
        for item in results
        if isinstance(item, Mapping)
    }
    if tuple(by_candidate) != EXPECTED_CANDIDATES:
        raise ValueError("full-stage candidate order changed")

    common_p0: object | None = None
    distilled_candidates: list[dict[str, object]] = []
    repetition_count = 0
    source_transition_steps = 0

    for source_id, machine_id in zip(EXPECTED_CANDIDATES, MACHINE_IDS, strict=True):
        record = by_candidate[source_id]
        if record.get("deterministic") is not True:
            raise ValueError(f"candidate is not deterministic: {source_id}")
        word_records = record.get("word_records")
        if not isinstance(word_records, Sequence) or isinstance(word_records, (str, bytes)):
            raise ValueError(f"word records missing: {source_id}")
        if [tuple(item["word"]) for item in word_records] != expected_words:
            raise ValueError(f"word order changed: {source_id}")

        distilled_words: list[dict[str, object]] = []
        for expected_word, word_record in zip(expected_words, word_records, strict=True):
            if word_record.get("deterministic") is not True:
                raise ValueError(f"nondeterministic source word: {source_id}/{expected_word}")
            repetitions = word_record.get("repetitions")
            if not isinstance(repetitions, Sequence) or len(repetitions) != 8:
                raise ValueError(f"incomplete repetition matrix: {source_id}/{expected_word}")
            traces = [item["trace"] for item in repetitions]
            if any(not isinstance(trace, Mapping) for trace in traces):
                raise ValueError("source trace must be an object")
            trace_hashes = sorted({sha256_bytes(canonical_bytes(trace)) for trace in traces})
            if trace_hashes != word_record.get("trace_sha256") or len(trace_hashes) != 1:
                raise ValueError(f"trace hash mismatch: {source_id}/{expected_word}")
            canonical_trace = traces[0]
            if any(trace != canonical_trace for trace in traces[1:]):
                raise ValueError(f"trace bytes disagree: {source_id}/{expected_word}")
            if tuple(canonical_trace.get("word", ())) != expected_word:
                raise ValueError(f"trace word mismatch: {source_id}/{expected_word}")
            steps = canonical_trace.get("steps")
            if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)):
                raise ValueError(f"trace steps missing: {source_id}/{expected_word}")
            if len(steps) != len(expected_word):
                raise ValueError(f"trace is not step-complete: {source_id}/{expected_word}")
            if [step.get("action") for step in steps] != list(expected_word):
                raise ValueError(f"trace actions disagree: {source_id}/{expected_word}")

            p0 = canonical_trace.get("p0")
            if common_p0 is None:
                common_p0 = p0
            elif p0 != common_p0:
                raise ValueError("candidate traces do not share one identical P0")

            projected = trace_projection(canonical_trace)
            distilled_words.append(
                {
                    "source_trace_sha256": trace_hashes[0],
                    "trace": projected,
                    "word": list(expected_word),
                }
            )
            repetition_count += len(repetitions)
            source_transition_steps += len(expected_word) * len(repetitions)

        distilled_candidates.append(
            {
                "bundle_manifest_sha256": record["bundle_manifest_sha256"],
                "machine_id": machine_id,
                "source_candidate_id": source_id,
                "word_records": distilled_words,
            }
        )

    if not isinstance(common_p0, Mapping):
        raise ValueError("common P0 was not recovered")
    distilled = {
        "audit_id": AUDIT_ID,
        "schema_version": 1,
        "source": {
            "audit_id": "OIA-1-TRACK-A-003b",
            "local_path": "local-work/track-a-003b/admission-results/FULL_RESULTS.json",
            "sha256": EXPECTED_FULL_RESULTS_SHA256,
        },
        "common_p0": common_p0,
        "actions": list(ACTIONS),
        "horizon": HORIZON,
        "candidates": distilled_candidates,
        "claim_boundary": (
            "Opened retrospective trace compilation only; the complete source traces "
            "and their known first divergence were already inspected."
        ),
    }
    validation = {
        "source_candidate_count": len(distilled_candidates),
        "source_word_count_per_candidate": len(expected_words),
        "source_repetitions_checked": repetition_count,
        "source_transition_steps_checked": source_transition_steps,
        "all_repetitions_exact": True,
        "one_identical_p0": True,
    }
    return distilled, validation


def build_adapter(source: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    prefixes = observed_prefixes()
    state_by_prefix = {prefix: f"S{index:03d}" for index, prefix in enumerate(prefixes)}
    sink_state = f"S{len(prefixes):03d}"
    state_manifest = {
        "audit_id": AUDIT_ID,
        "states": {
            state: {"access_word": list(prefix), "kind": "observed_prefix"}
            for prefix, state in state_by_prefix.items()
        }
        | {sink_state: {"access_word": None, "kind": "out_of_scope_sink"}},
    }
    output_manifest: dict[str, object] = {
        BOUNDARY_OUTPUT: {
            "kind": "adapter_boundary",
            "reason": "action requested after the frozen depth-3 trace envelope",
        }
    }
    machines: list[dict[str, object]] = []
    candidate_checks: list[dict[str, object]] = []

    raw_candidates = source.get("candidates")
    if not isinstance(raw_candidates, Sequence) or isinstance(raw_candidates, (str, bytes)):
        raise ValueError("source candidates must be an array")

    for candidate in raw_candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("source candidate must be an object")
        machine_id = str(candidate["machine_id"])
        source_id = str(candidate["source_candidate_id"])
        step_by_prefix: dict[tuple[str, ...], Mapping[str, object]] = {}
        record_by_word: dict[tuple[str, ...], Mapping[str, object]] = {}

        for record in candidate["word_records"]:
            word = tuple(record["word"])
            trace = record["trace"]
            if not isinstance(trace, Mapping):
                raise ValueError("distilled trace must be an object")
            record_by_word[word] = trace
            for index, step in enumerate(trace["steps"], start=1):
                prefix = word[:index]
                if not isinstance(step, Mapping):
                    raise ValueError("trace step must be an object")
                previous = step_by_prefix.setdefault(prefix, step)
                if previous != step:
                    raise ValueError(
                        f"prefix-inconsistent source trace: {source_id}/{prefix}"
                    )

        if set(step_by_prefix) != set(frozen_words()):
            raise ValueError(f"source does not cover every observed prefix: {source_id}")

        transitions: dict[str, dict[str, dict[str, str]]] = {}
        for prefix, state in state_by_prefix.items():
            transitions[state] = {}
            for action in ACTIONS:
                if len(prefix) < HORIZON:
                    successor_prefix = prefix + (action,)
                    observation = observation_projection(step_by_prefix[successor_prefix])
                    output = observation_id(observation)
                    previous = output_manifest.setdefault(output, observation)
                    if previous != observation:
                        raise RuntimeError("observation encoder collision")
                    next_state = state_by_prefix[successor_prefix]
                else:
                    output = BOUNDARY_OUTPUT
                    next_state = sink_state
                transitions[state][action] = {
                    "next_state": next_state,
                    "output": output,
                }
        transitions[sink_state] = {
            action: {"next_state": sink_state, "output": BOUNDARY_OUTPUT}
            for action in ACTIONS
        }

        machines.append(
            {
                "name": machine_id,
                "initial_state": state_by_prefix[()],
                "metadata": {
                    "adapter": "bounded_prefix_tree_v1",
                    "horizon": HORIZON,
                    "source_bundle_manifest_sha256": candidate["bundle_manifest_sha256"],
                    "source_candidate_id_sha256": sha256_bytes(source_id.encode("utf-8")),
                },
                "transitions": transitions,
            }
        )

        replayed_words = 0
        replayed_steps = 0
        for word in frozen_words():
            state = state_by_prefix[()]
            observed: list[str] = []
            for action in word:
                transition = transitions[state][action]
                observed.append(transition["output"])
                state = transition["next_state"]
            expected = [
                observation_id(observation_projection(step))
                for step in record_by_word[word]["steps"]
            ]
            if observed != expected:
                raise AssertionError(f"adapter replay mismatch: {source_id}/{word}")
            replayed_words += 1
            replayed_steps += len(word)
        candidate_checks.append(
            {
                "machine_id": machine_id,
                "source_candidate_id": source_id,
                "words_replayed": replayed_words,
                "transition_steps_replayed": replayed_steps,
                "result": "pass",
            }
        )

    audit_input = {
        "machines": machines,
        "options": {
            "max_beliefs": 100_000,
            "max_partitions": 100_000,
            "value_depth": HORIZON,
            "max_task_loss_frontier": 50_000,
        },
    }
    validation = {
        "audit_id": AUDIT_ID,
        "adapter": "bounded_prefix_tree_v1",
        "validation": "complete_frozen_word_replay",
        "candidate_count": len(machines),
        "actions": list(ACTIONS),
        "horizon": HORIZON,
        "observed_prefix_states_per_candidate": len(prefixes),
        "out_of_scope_sink_states_per_candidate": 1,
        "complete_machine_states_per_candidate": len(prefixes) + 1,
        "complete_machine_edges_per_candidate": (len(prefixes) + 1) * len(ACTIONS),
        "words_replayed_total": sum(row["words_replayed"] for row in candidate_checks),
        "transition_steps_replayed_total": sum(
            row["transition_steps_replayed"] for row in candidate_checks
        ),
        "boundary_output_candidate_independent": True,
        "candidate_checks": candidate_checks,
        "result": "pass",
    }
    return audit_input, output_manifest, state_manifest, validation


def instrument_provenance() -> dict[str, object]:
    records = []
    for relative in FROZEN_INSTRUMENT_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        records.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "audit_id": AUDIT_ID,
        "accepted_baseline": "OIA-1 v0.2.1",
        "accepted_package_sha256": "2653020afcbf636def260da1517c9e3ba41c2ba1175fc210d4847b303febc33b",
        "source_import": "executable-ontology-lab commit 3ca35d4",
        "files": records,
    }


def protocol(source: Mapping[str, object]) -> dict[str, object]:
    return {
        "audit_id": AUDIT_ID,
        "schema_version": 1,
        "track": "A_opened_retrospective_adapter_integration",
        "status_at_freeze": "frozen_before_full_track_a_004a_audit_execution",
        "freeze_date": "2026-08-21",
        "predecessor": {
            "audit_id": "OIA-1-TRACK-A-003b",
            "gate_verdict": "candidate_frontier_feasible",
            "full_results_sha256": EXPECTED_FULL_RESULTS_SHA256,
        },
        "epistemic_ordering": {
            "complete_candidate_traces_already_known": True,
            "first_divergence_already_known": True,
            "engineering_pairwise_precheck_already_run": True,
            "adapter_and_oia_input_frozen_before_full_audit_run": True,
            "classification": "retrospective_external_instrument_validation",
            "prospective_separator_discovery_claim_allowed": False,
        },
        "candidate_mapping": [
            {
                "machine_id": candidate["machine_id"],
                "source_candidate_id": candidate["source_candidate_id"],
                "bundle_manifest_sha256": candidate["bundle_manifest_sha256"],
            }
            for candidate in source["candidates"]
        ],
        "intervention_boundary": {
            "actions": list(ACTIONS),
            "maximum_observed_depth": HORIZON,
            "word_count_per_candidate": len(frozen_words()),
            "source": "deterministic predictions archived by Track A 003b",
            "real_arc_actions_authorized": False,
            "candidate_execution_authorized": False,
        },
        "adapter_contract": {
            "kind": "complete deterministic bounded prefix-tree Mealy compilation",
            "observation_fields": [
                "status",
                "error_category",
                "final_frame_sha256",
                "modeled_progress",
            ],
            "all_observed_prefixes_required": True,
            "all_84_words_replayed_per_candidate": True,
            "post_horizon_behavior": "candidate-independent out-of-scope sink",
            "separator_specific_logic_forbidden": True,
        },
        "execution_plan": {
            "engine": "unchanged accepted OIA-1 v0.2.1",
            "entry_point": "ontology_auditor.io.audit_payload",
            "pythonhashseed_values": [0, 1, 5, 10],
            "exact_report_bytes_required_across_processes": True,
            "primary_endpoint": "full_candidate_identification.adaptive",
            "independent_checks": [
                "serialized adaptive witness verification",
                "minimum pairwise separator comparison against frozen source traces",
                "policy black-box replay against frozen source traces",
            ],
        },
        "allowed_success_claim": (
            "The unchanged accepted OIA v0.2.1 retrospectively reconstructs and "
            "certifies a minimum separator for the two admitted predictive programs "
            "within the frozen opened depth-3 trace envelope."
        ),
        "not_supported": [
            "prospective discovery of an unknown separator",
            "correctness of either predictive program",
            "a real ARC outcome or intervention benefit",
            "ontology revision necessity or planning superiority",
            "sealed transfer or Track B claims",
        ],
        "prohibited_during_gate": [
            "real ARC actions",
            "candidate execution",
            "model or API calls",
            "credentials or hosted services",
            "private or sealed evaluation",
            "changes to accepted OIA v0.2.1",
        ],
    }


def write_json(path: Path, value: object) -> None:
    path.write_bytes(pretty_bytes(value))


def write_pre_run_checksums() -> None:
    relatives = [f"audits/track-a-004a/{name}" for name in PRE_RUN_ARTIFACT_NAMES]
    relatives.extend(PRE_RUN_SOURCE_PATHS)
    lines = []
    for relative in sorted(relatives):
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        lines.append(f"{sha256_file(path)}  {relative}")
    (AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-results", type=Path, default=DEFAULT_FULL_RESULTS)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if (AUDIT_ROOT / "outcome").exists():
        raise RuntimeError("Track A 004a outcome exists; refusing to refreeze")
    existing = [AUDIT_ROOT / name for name in PRE_RUN_ARTIFACT_NAMES]
    existing.append(AUDIT_ROOT / "PRE_RUN_SHA256SUMS.txt")
    if not args.force and any(path.exists() for path in existing):
        raise RuntimeError("pre-run artifacts already exist; use --force only before execution")

    source_path = args.full_results.resolve()
    if sha256_file(source_path) != EXPECTED_FULL_RESULTS_SHA256:
        raise ValueError("Track A 003b full-results hash mismatch")
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    if summary["raw_evidence"]["full_results"]["sha256"] != EXPECTED_FULL_RESULTS_SHA256:
        raise ValueError("committed Track A 003b summary has a different source hash")
    full_results = json.loads(source_path.read_text(encoding="utf-8"))
    source, source_validation = validate_and_distill(full_results)
    audit_input, outputs, states, adapter_validation = build_adapter(source)

    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(AUDIT_ROOT / "ADAPTER_SOURCE_TRACES.json", source)
    write_json(
        AUDIT_ROOT / "ENGINEERING_PRECHECK.pre-full-audit.json",
        {
            "audit_id": AUDIT_ID,
            "schema_version": 1,
            "status": "preserved_engineering_precheck",
            "occurred_after_initial_generation_before_main_merge": True,
            "operation": (
                "Loaded the generated CandidateSystem and called the accepted "
                "shortest_pairwise_separator routine once."
            ),
            "observed_result": {
                "distinguishable": True,
                "left": "C0001",
                "right": "C0002",
                "sequence": ["ACTION2"],
            },
            "prior_knowledge": (
                "Track A 003b had already published ACTION2 as the first divergence, "
                "so the precheck added no new epistemic access."
            ),
            "full_audit_executed": False,
            "candidate_processes": 0,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
            "model_or_api_calls": 0,
            "correction": (
                "Preserve this event and refreeze the complete package before any "
                "full audit_payload/CLI execution; make no prospective claim."
            ),
        },
    )
    write_json(AUDIT_ROOT / "OIA_INPUT.frozen.json", audit_input)
    write_json(
        AUDIT_ROOT / "OUTPUT_MANIFEST.opened.json",
        {"audit_id": AUDIT_ID, "outputs": outputs},
    )
    write_json(AUDIT_ROOT / "STATE_MANIFEST.opened.json", states)
    write_json(
        AUDIT_ROOT / "TRACE_PRESERVATION.json",
        {
            "audit_id": AUDIT_ID,
            "schema_version": 1,
            "source_validation": source_validation,
            "adapter_validation": adapter_validation,
            "result": "pass",
        },
    )
    write_json(AUDIT_ROOT / "INSTRUMENT_SOURCE_PROVENANCE.json", instrument_provenance())
    write_json(AUDIT_ROOT / "RETROSPECTIVE_PROTOCOL.frozen.json", protocol(source))
    write_pre_run_checksums()
    print(
        json.dumps(
            {
                "audit_id": AUDIT_ID,
                "input_sha256": sha256_file(AUDIT_ROOT / "OIA_INPUT.frozen.json"),
                "source_words": len(frozen_words()) * len(EXPECTED_CANDIDATES),
                "status": "pre_run_frozen",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
