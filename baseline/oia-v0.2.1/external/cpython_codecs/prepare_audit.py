"""Freeze Track-A audit 002 without consulting its prospective target outcome."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from codec_adapter import (
    CANDIDATE_CODECS,
    DIAGNOSTIC_BYTES,
    HORIZON,
    OUTSIDE_TARGET_CODEC,
    action_encoder,
    candidate_id,
    decision_id,
    label_id,
    runtime_provenance,
    target_id,
)
from validate_adapter import validate_family

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT_ID = "OIA-1-TRACK-A-002"
AUDIT_DIR = HERE / "audit_002"

INSTRUMENT_RELATIVE_PATHS = (
    "src/ontology_auditor/model.py",
    "src/ontology_auditor/equivalence.py",
    "src/ontology_auditor/synthesis.py",
    "src/ontology_auditor/decision.py",
    "src/ontology_auditor/task_loss.py",
    "src/ontology_auditor/audit.py",
    "src/ontology_auditor/io.py",
    "external/cpython_codecs/codec_adapter.py",
    "external/cpython_codecs/validate_adapter.py",
    "external/cpython_codecs/prepare_audit.py",
    "external/cpython_codecs/run_opened_audit.py",
    "external/cpython_codecs/execute_prospective_outcome.py",
    "tests/test_auditor.py",
    "tests/test_track_a_codec.py",
)


def canonical_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, payload: object) -> None:
    path.write_text(canonical_json(payload), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_checksum_manifest(path: Path, files: list[Path]) -> None:
    lines = [f"{sha256(item)}  {item.relative_to(AUDIT_DIR)}" for item in sorted(files)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def instrument_source_provenance() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for relative in INSTRUMENT_RELATIVE_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"frozen instrument source missing: {relative}")
        records.append(
            {
                "path": relative,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "audit_id": AUDIT_ID,
        "hash_algorithm": "SHA-256",
        "purpose": (
            "freeze the exact OIA core, substrate adapter, validators, outcome "
            "runner, and regression tests before prospective execution"
        ),
        "files": records,
    }


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if (AUDIT_DIR / "prospective_outcome.json").exists():
        raise RuntimeError("audit 002 already has an outcome; refusing to refreeze")

    actions_by_id, _ = action_encoder()
    adapted, validation = validate_family(CANDIDATE_CODECS, horizon=HORIZON)

    candidate_map = {
        model.machine.name: source
        for source, model in zip(CANDIDATE_CODECS, adapted, strict=True)
    }
    multibyte_class = label_id("streaming_multibyte")
    single_byte_class = label_id("single_byte")
    labels = {
        candidate_id(name): (
            multibyte_class if name in {"utf-8", "utf-8-sig"} else single_byte_class
        )
        for name in CANDIDATE_CODECS
    }
    streaming_decision = decision_id("use_streaming_multibyte_path")
    single_decision = decision_id("use_single_byte_path")
    decisions = (streaming_decision, single_decision)
    utilities = {
        model_id: {
            streaming_decision: 1.0 if labels[model_id] == multibyte_class else 0.0,
            single_decision: 1.0 if labels[model_id] == single_byte_class else 0.0,
        }
        for model_id in labels
    }

    audit_input = {
        "machines": [item.machine.to_dict() for item in adapted],
        "labels": labels,
        "decision_problem": {
            "decisions": list(decisions),
            "utilities": utilities,
        },
        "priors": {model_id: 1.0 / len(adapted) for model_id in labels},
        "action_costs": {action_id: 0.01 for action_id in actions_by_id},
        "options": {
            "max_beliefs": 500_000,
            "max_partitions": 500_000,
            "value_depth": HORIZON,
            "max_task_loss_frontier": 50_000,
        },
    }

    output_manifest: dict[str, object] = {}
    state_manifests: dict[str, object] = {}
    access_words: dict[str, object] = {}
    for item in adapted:
        for output, source in item.output_manifest.items():
            if output in output_manifest and output_manifest[output] != source:
                raise RuntimeError("output encoder collision")
            output_manifest[output] = source
        state_manifests[item.machine.name] = item.state_manifest
        access_words[item.machine.name] = {
            state: list(word) for state, word in sorted(item.access_words.items())
        }

    provenance = runtime_provenance(CANDIDATE_CODECS + (OUTSIDE_TARGET_CODEC,))
    provenance.update(
        {
            "audit_id": AUDIT_ID,
            "substrate": "CPython incremental codec registry",
            "upstream_project": "CPython",
            "upstream_license": "Python Software Foundation License Version 2",
            "license_url": "https://docs.python.org/3/license.html",
            "documentation_url": "https://docs.python.org/3/library/codecs.html",
            "candidate_family_source": (
                "stdlib codec implementations installed with the frozen CPython runtime"
            ),
            "candidate_codecs": list(CANDIDATE_CODECS),
            "outside_target_codec": OUTSIDE_TARGET_CODEC,
        }
    )

    protocol = {
        "audit_id": AUDIT_ID,
        "audit_number": 2,
        "track": "A_opened_external_instrument_validation",
        "status_at_freeze": "opened_outcome_not_yet_executed",
        "freeze_date": "2026-08-21",
        "predecessor": {
            "audit_id": "OIA-1-TRACK-A-001",
            "status": "closed_pre_outcome_instrument_failure",
            "outcome_consulted": False,
            "reason": "behavioral partition block-ID relabeling prevented termination",
        },
        "candidate_set": list(CANDIDATE_CODECS),
        "diagnostic_byte_alphabet": list(DIAGNOSTIC_BYTES),
        "candidate_ids": sorted(candidate_map),
        "prospective_target": OUTSIDE_TARGET_CODEC,
        "prospective_target_id": target_id(OUTSIDE_TARGET_CODEC),
        "target_membership": "outside_frozen_candidate_set",
        "adapter": "cpython_incremental_codec_finite_horizon_v1",
        "adapter_boundary": {
            "reset": "fresh strict incremental decoder",
            "inputs": "six frozen diagnostic one-byte pushes plus explicit finish",
            "outputs": (
                "Unicode codepoint vector, normalized decode_error, or terminal/horizon token"
            ),
            "error_semantics": "first strict UnicodeDecodeError closes the episode",
            "horizon_actions": HORIZON,
            "completion": (
                "common explicit horizon/closed sinks make every adapted machine finite "
                "and input-complete"
            ),
        },
        "encoder": {
            "algorithm": "SHA-256 over canonical JSON, first 16 hexadecimal digits",
            "OIA_visibility": "opaque IDs only",
            "opened_sidecar": "encoder_manifest.opened.json",
        },
        "primary_target": "full candidate identity",
        "primary_policy": (
            "minimum-worst-case adaptive policy if exact; otherwise verified witness only"
        ),
        "secondary_target": "two-class decoder-mode distinction",
        "decision_criterion": {
            "choices": ["streaming_multibyte_path", "single_byte_path"],
            "utility": (
                "1 for the path assigned to the candidate codec family, 0 otherwise"
            ),
            "action_cost": 0.01,
            "interpretation": (
                "instrument-level routing decision only; not an operational superiority claim"
            ),
        },
        "caps": audit_input["options"],
        "prospective_execution_rule": (
            "after OIA selection and pre-outcome checksum freeze, execute the primary "
            "adaptive policy once against a fresh cp437 decoder; report outside_model "
            "immediately if the encoded observation is absent from the policy branches"
        ),
        "black_box_comparison": (
            "replay the selected policy against reset-and-query candidate codec oracles "
            "without reading compiled states; compare branch traces and witness depth only"
        ),
        "comparative_value_claim": False,
        "claim_boundary": (
            "opened adapter fidelity, exact/cap behavior, prospective separator execution, "
            "decision-vs-identity efficiency, outside-model detection, and scaling only"
        ),
        "instrument_source_freeze": "instrument_source_provenance.json",
    }

    encoder_manifest = {
        "audit_id": protocol["audit_id"],
        "actions": actions_by_id,
        "candidates": candidate_map,
        "labels": {
            multibyte_class: "streaming_multibyte",
            single_byte_class: "single_byte",
        },
        "decisions": {
            streaming_decision: "use_streaming_multibyte_path",
            single_decision: "use_single_byte_path",
        },
        "outputs_observed_during_candidate_compilation": dict(
            sorted(output_manifest.items())
        ),
        "prospective_target": {
            "target_id": target_id(OUTSIDE_TARGET_CODEC),
            "codec": OUTSIDE_TARGET_CODEC,
        },
    }

    source_screening = {
        "audit_id": AUDIT_ID,
        "screen_date": "2026-08-21",
        "selection_rule": (
            "prefer a public licensed resettable deterministic family whose exact source "
            "bytes can be frozen and whose traces can be replayed independently"
        ),
        "options": [
            {
                "name": "Automata Wiki / AALpy MQTT Mealy models",
                "public_urls": [
                    "https://automata.cs.ru.nl/BenchmarkMQTT/",
                    "https://github.com/DES-Lab/AALpy",
                ],
                "strength": (
                    "independently authored shared-alphabet protocol model family"
                ),
                "result": "not_selected_acquisition_failure",
                "reason": (
                    "the exact public model archive/source files could not be materialized "
                    "reproducibly in this execution environment, so their bytes and license "
                    "could not be frozen into the package"
                ),
                "outcomes_consulted": False,
            },
            {
                "name": "CPython incremental codec implementations",
                "public_urls": [
                    "https://docs.python.org/3/library/codecs.html",
                    "https://docs.python.org/3/license.html",
                ],
                "strength": (
                    "public licensed deterministic resettable implementations already "
                    "present with source-file provenance in the runtime"
                ),
                "result": "selected",
                "reason": (
                    "five externally implemented candidates and one outside-model target "
                    "could be frozen byte-for-byte and exhaustively replayed through a "
                    "small finite-horizon adapter"
                ),
                "outcomes_consulted_before_freeze": False,
            },
        ],
    }

    engineering_negative = {
        "audit_id": "OIA-1-TRACK-A-000",
        "date": "2026-08-21",
        "attempt": "all 256 one-byte pushes plus finish, horizon 4",
        "validation": "complete reachable-state and edge replay",
        "engineering_cap_seconds": 120,
        "result": "cap_limited_noncompletion",
        "artifacts_produced": False,
        "interpretation": (
            "the initial all-byte adapter validation did not complete inside the "
            "engineering cap; this is a real scaling negative, not evidence of "
            "identifiability or non-identifiability"
        ),
        "next_numbered_audit": (
            "audit 001 froze a seven-action opened diagnostic alphabet before "
            "running OIA or the prospective target"
        ),
    }

    paths = {
        "audit_000_engineering_negative.json": engineering_negative,
        "audit_input.opaque.json": audit_input,
        "audit_protocol.frozen.json": protocol,
        "encoder_manifest.opened.json": encoder_manifest,
        "source_provenance.json": provenance,
        "source_screening.json": source_screening,
        "instrument_source_provenance.json": instrument_source_provenance(),
        "adapter_trace_validation.json": validation,
        "adapter_state_manifest.json": state_manifests,
        "adapter_access_words.json": access_words,
    }
    written: list[Path] = []
    for name, payload in paths.items():
        path = AUDIT_DIR / name
        write_json(path, payload)
        written.append(path)

    freeze_manifest = AUDIT_DIR / "FREEZE_SHA256SUMS"
    write_checksum_manifest(freeze_manifest, written)
    print(f"frozen {protocol['audit_id']}")
    print(f"candidates={len(adapted)} actions={len(actions_by_id)} horizon={HORIZON}")
    print(
        f"trace_validation_states={validation['total_states_checked']} "
        f"edges={validation['total_edges_checked']}"
    )
    print(f"wrote {freeze_manifest}")


if __name__ == "__main__":
    main()
