"""Fail-closed context adapter for prospective DiscoverPhysics-style studies.

This module only validates and packages already-authorized records. It does not
import DiscoverPhysics, execute a simulator, call a model, inspect a private
world, or score a candidate law.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "OIA-DISCOVERPHYSICS-CONTEXT-ADAPTER-0.1"
SOURCE_COMMIT = "33b7fa9df96de9c35744efd181ca7e5a8dd60ad5"
SOURCE_TREE = "68cb921b1c7347e78161622fb44194c7fa6d16b3"
EXPERIMENT_CONTEXT_FIELDS = (
    "p1",
    "p2",
    "pos2",
    "velocity2",
    "start_time",
)
CANDIDATE_INPUT_FIELDS = (
    "pos1",
    "pos2",
    "p1",
    "p2",
    "velocity2",
    "start_time",
    "duration",
)
MATCHED_PAIR_FIELDS = (
    "p1",
    "p2",
    "pos2",
    "velocity2",
    "measurement_times",
    "start_time",
    "duration",
)
ALLOWED_EVENT_KINDS = frozenset(
    {
        "experiment_request",
        "experiment_observation",
        "hypothesis_revision",
        "resource_snapshot",
        "artifact_submission",
    }
)
FORBIDDEN_LEARNER_KEYS = frozenset(
    {
        "evaluation_threshold",
        "held_out_outcome",
        "held_out_trajectory",
        "private_evaluator_source",
        "private_world_source",
        "true_law",
    }
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _unique_strings(values: Any, label: str) -> tuple[str, ...]:
    _require(isinstance(values, list) and values, f"{label} must be a non-empty list")
    _require(
        all(isinstance(value, str) and value for value in values),
        f"{label} must contain non-empty strings",
    )
    result = tuple(values)
    _require(len(set(result)) == len(result), f"{label} contains duplicates")
    return result


def _number(value: Any, label: str) -> float:
    _require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{label} must be numeric",
    )
    result = float(value)
    _require(math.isfinite(result), f"{label} must be finite")
    return result


def _vector2(value: Any, label: str) -> list[float]:
    _require(isinstance(value, list) and len(value) == 2, f"{label} must be length 2")
    return [_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if isinstance(key, str):
                yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def validate_learner_visible(value: Any, label: str = "learner-visible payload") -> None:
    forbidden = sorted(FORBIDDEN_LEARNER_KEYS.intersection(_walk_keys(value)))
    _require(not forbidden, f"{label} contains forbidden private fields: {forbidden}")


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(contract, Mapping), "adapter contract must be an object")
    _require(contract.get("schema_version") == SCHEMA_VERSION, "adapter schema changed")
    source = contract.get("source") or {}
    _require(source.get("commit") == SOURCE_COMMIT, "source commit changed")
    _require(source.get("tree") == SOURCE_TREE, "source tree changed")

    interface = contract.get("artifact_interface") or {}
    experiment_fields = _unique_strings(
        interface.get("experiment_context_fields"), "experiment context fields"
    )
    candidate_fields = _unique_strings(
        interface.get("candidate_input_fields"), "candidate input fields"
    )
    evaluator_fields = _unique_strings(
        interface.get("evaluator_forwarded_fields"), "evaluator forwarded fields"
    )
    _require(
        experiment_fields == EXPERIMENT_CONTEXT_FIELDS,
        "experiment context field set changed",
    )
    _require(candidate_fields == CANDIDATE_INPUT_FIELDS, "candidate interface changed")
    _require(
        evaluator_fields == CANDIDATE_INPUT_FIELDS,
        "evaluator does not forward the complete candidate context",
    )
    _require(
        set(experiment_fields) <= set(candidate_fields),
        "candidate interface loses intervention context",
    )
    _require(
        interface.get("serialization") == "canonical_json_utf8_sorted_keys_no_nan",
        "context serialization changed",
    )

    pair = contract.get("matched_pair") or {}
    _require(pair.get("changed_field") == "start_time", "matched-pair field changed")
    _require(
        tuple(pair.get("comparison_fields") or ()) == MATCHED_PAIR_FIELDS,
        "matched-pair comparison fields changed",
    )
    _require(
        pair.get("pair_values") is None
        and pair.get("outcomes") is None
        and pair.get("thresholds") is None,
        "private matched-pair material entered the pre-custody contract",
    )
    _require(
        pair.get("custodian_commitment_required") is True,
        "custodian pair commitment is not required",
    )
    _require(
        pair.get("commitment_algorithm")
        == "sha256_of_canonical_json_pair_source_commit_and_custodian_nonce"
        and pair.get("custodian_nonce_minimum_bits") == 128
        and pair.get("custodian_nonce_hidden_until_commitment_opening") is True,
        "matched-pair commitment is not hiding",
    )

    trace = contract.get("trace_contract") or {}
    _require(
        tuple(trace.get("event_kinds") or ()) == tuple(sorted(ALLOWED_EVENT_KINDS)),
        "trace event-kind contract changed",
    )
    _require(trace.get("strictly_contiguous_sequence") is True, "trace ordering weakened")
    _require(trace.get("context_preserved_exactly") is True, "trace context preservation weakened")

    custody = contract.get("custody_boundary") or {}
    for field in (
        "private_world_source_learner_hidden",
        "true_law_learner_hidden",
        "held_out_pair_learner_hidden",
        "outcomes_and_thresholds_learner_hidden_until_submission",
        "same_pair_scores_L0_and_L1",
    ):
        _require(custody.get(field) is True, f"custody boundary weakened: {field}")

    execution = contract.get("execution_boundary") or {}
    for field, value in execution.items():
        _require(value == 0, f"adapter contract crossed execution boundary: {field}")
    _require(execution, "execution boundary is missing")

    claims = contract.get("claim_boundary") or {}
    _require(claims.get("project_reopening_effect") == "none", "project gate changed")
    _require(
        claims.get("broad_ontology_formation_claim_reopened") is False,
        "broad ontology claim was reopened",
    )
    _require(
        claims.get("maximum_pre_outcome_claim")
        == "context_complete_adapter_engineering_qualification",
        "pre-outcome claim broadened",
    )
    _require(
        contract.get("status") == "context_adapter_frozen_unexecuted",
        "adapter contract status changed",
    )
    return deepcopy(dict(contract))


def validate_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(experiment, Mapping), "experiment must be an object")
    validate_learner_visible(experiment, "experiment")
    missing = [field for field in MATCHED_PAIR_FIELDS if field not in experiment]
    _require(not missing, f"experiment is missing fields: {missing}")
    _number(experiment["p1"], "p1")
    _number(experiment["p2"], "p2")
    _vector2(experiment["pos2"], "pos2")
    _vector2(experiment["velocity2"], "velocity2")
    _number(experiment["start_time"], "start_time")
    _require(_number(experiment["duration"], "duration") > 0.0, "duration must be positive")
    times = experiment["measurement_times"]
    _require(isinstance(times, list) and times, "measurement_times must be non-empty")
    numeric_times = [_number(value, f"measurement_times[{index}]") for index, value in enumerate(times)]
    _require(numeric_times == sorted(numeric_times), "measurement_times must be sorted")
    _require(
        all(0.0 <= value <= float(experiment["duration"]) for value in numeric_times),
        "measurement_times fall outside duration",
    )
    return deepcopy(dict(experiment))


def build_candidate_call(
    contract: Mapping[str, Any],
    experiment: Mapping[str, Any],
    duration: float,
    *,
    pos1: list[float] | None = None,
) -> dict[str, Any]:
    """Build one evaluator call without dropping intervention context."""

    validate_contract(contract)
    normalized = validate_experiment(experiment)
    call_duration = _number(duration, "candidate duration")
    _require(call_duration >= 0.0, "candidate duration must be non-negative")
    _require(
        call_duration <= float(normalized["duration"]),
        "candidate duration exceeds experiment duration",
    )
    values: dict[str, Any] = {
        "pos1": _vector2(pos1 if pos1 is not None else [0.0, 0.0], "pos1"),
        "pos2": deepcopy(normalized["pos2"]),
        "p1": normalized["p1"],
        "p2": normalized["p2"],
        "velocity2": deepcopy(normalized["velocity2"]),
        "start_time": normalized["start_time"],
        "duration": call_duration,
    }
    _require(tuple(values) == CANDIDATE_INPUT_FIELDS, "candidate call ordering changed")
    return values


def commit_matched_pair(
    contract: Mapping[str, Any],
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    commitment_nonce: str,
) -> dict[str, Any]:
    """Validate a custodian-side pair and return only its hiding commitment."""

    validate_contract(contract)
    _require(
        isinstance(commitment_nonce, str)
        and len(commitment_nonce) >= 32
        and len(commitment_nonce) % 2 == 0
        and all(character in "0123456789abcdef" for character in commitment_nonce),
        "commitment nonce must be at least 128 bits of lowercase hexadecimal",
    )
    left_normalized = validate_experiment(left)
    right_normalized = validate_experiment(right)
    differing = [
        field
        for field in MATCHED_PAIR_FIELDS
        if left_normalized[field] != right_normalized[field]
    ]
    _require(differing == ["start_time"], f"matched pair differs in fields: {differing}")
    commitment_payload = {
        "schema_version": SCHEMA_VERSION,
        "changed_field": "start_time",
        "left": {field: left_normalized[field] for field in MATCHED_PAIR_FIELDS},
        "right": {field: right_normalized[field] for field in MATCHED_PAIR_FIELDS},
        "source_commit": SOURCE_COMMIT,
        "custodian_nonce": commitment_nonce,
    }
    return {
        "schema_version": "OIA-DISCOVERPHYSICS-MATCHED-PAIR-COMMITMENT-0.1",
        "changed_field": "start_time",
        "comparison_fields": list(MATCHED_PAIR_FIELDS),
        "commitment_sha256": canonical_sha256(commitment_payload),
        "commitment_nonce_disclosed": False,
        "pair_values_disclosed": False,
        "outcomes_disclosed": False,
    }


def validate_trace(
    contract: Mapping[str, Any], events: list[Mapping[str, Any]]
) -> dict[str, Any]:
    """Validate a complete learner-visible trace without executing or scoring it."""

    validate_contract(contract)
    _require(isinstance(events, list) and events, "trace must be a non-empty list")
    validate_learner_visible(events, "trace")
    requests: dict[int, tuple[int, dict[str, Any]]] = {}
    kinds: list[str] = []
    previous_round = 0
    for expected_sequence, event in enumerate(events):
        _require(isinstance(event, Mapping), f"event {expected_sequence} is not an object")
        _require(
            event.get("sequence") == expected_sequence,
            "trace sequence is not strictly contiguous",
        )
        round_number = event.get("round")
        _require(
            isinstance(round_number, int) and not isinstance(round_number, bool) and round_number >= 1,
            f"event {expected_sequence} has invalid round",
        )
        _require(round_number >= previous_round, "trace rounds move backwards")
        previous_round = round_number
        kind = event.get("kind")
        _require(kind in ALLOWED_EVENT_KINDS, f"event {expected_sequence} has invalid kind")
        payload = event.get("payload")
        _require(isinstance(payload, Mapping), f"event {expected_sequence} payload missing")
        kinds.append(kind)

        if kind == "experiment_request":
            requests[expected_sequence] = (round_number, validate_experiment(payload))
        elif kind == "experiment_observation":
            request_sequence = payload.get("experiment_sequence")
            _require(request_sequence in requests, "observation does not reference an earlier request")
            request_round, request = requests[request_sequence]
            _require(request_round == round_number, "observation round differs from request round")
            _require(
                payload.get("measurement_times") == request["measurement_times"],
                "observation measurement context changed",
            )
            _require(
                payload.get("start_time") == request["start_time"],
                "observation dropped or changed start_time",
            )
            for field in ("pos1", "pos2", "velocity1", "velocity2"):
                _require(field in payload, f"observation lacks {field}")
        elif kind == "hypothesis_revision":
            _require(
                isinstance(payload.get("hypothesis_id"), str)
                and payload["hypothesis_id"],
                "hypothesis revision lacks an id",
            )
            _require(
                isinstance(payload.get("hypothesis"), str) and payload["hypothesis"],
                "hypothesis revision lacks content",
            )
        elif kind == "resource_snapshot":
            for field in ("model_calls", "elapsed_seconds", "input_tokens", "output_tokens"):
                _require(field in payload, f"resource snapshot lacks {field}")
                _require(_number(payload[field], field) >= 0.0, f"{field} must be non-negative")
        elif kind == "artifact_submission":
            digest = payload.get("artifact_sha256")
            _require(
                isinstance(digest, str)
                and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                "artifact submission has invalid SHA-256",
            )
            _require(
                tuple(payload.get("interface_fields") or ()) == CANDIDATE_INPUT_FIELDS,
                "submitted artifact interface loses context",
            )

    for required_kind in (
        "experiment_request",
        "experiment_observation",
        "hypothesis_revision",
        "resource_snapshot",
        "artifact_submission",
    ):
        _require(required_kind in kinds, f"trace lacks {required_kind}")
    _require(kinds[-1] == "artifact_submission", "trace does not end at submission")
    return {
        "schema_version": "OIA-DISCOVERPHYSICS-TRACE-VALIDATION-0.1",
        "events": len(events),
        "experiments": len(requests),
        "first_sequence": 0,
        "last_sequence": len(events) - 1,
        "trace_sha256": canonical_sha256(events),
        "context_complete": True,
        "model_calls_performed_by_validation": 0,
        "simulator_calls_performed_by_validation": 0,
    }
