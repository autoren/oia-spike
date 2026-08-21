"""Opened Track-A adapter for CPython incremental text decoders.

This is deliberately substrate-specific, not an AOEL compiler.  It exposes a
finite-horizon, deterministic, resettable input/output slice of independently
implemented CPython codecs as complete Mealy machines.  The OIA core sees only
opaque candidate, action, state, output, and decision identifiers.
"""

from __future__ import annotations

import codecs
import hashlib
import inspect
import json
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ontology_auditor import MealyMachine, Transition

CANDIDATE_CODECS = ("utf-8", "utf-8-sig", "latin-1", "cp1252", "iso8859-15")
OUTSIDE_TARGET_CODEC = "cp437"
HORIZON = 4
DIAGNOSTIC_BYTES = (0x41, 0x80, 0xA4, 0xBB, 0xBF, 0xEF)


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def opaque_id(prefix: str, payload: object) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("ascii")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def action_specs() -> tuple[dict[str, object], ...]:
    """Frozen opened diagnostic alphabet for audits 001 and 002.

    Audit 000 attempted all 256 one-byte pushes plus ``finish``; complete
    reachable-edge validation did not finish within the 120-second engineering
    cap.  Audits 001 and 002 therefore use six predeclared diagnostic bytes plus
    ``finish``.  This is an opened instrument-validation choice, not a sealed
    discovery claim.
    """

    return tuple(
        [{"kind": "push_byte", "value": value} for value in DIAGNOSTIC_BYTES]
        + [{"kind": "finish"}]
    )


def action_encoder() -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    by_id: dict[str, dict[str, object]] = {}
    by_source: dict[str, str] = {}
    for spec in action_specs():
        action_id = opaque_id("a", spec)
        if action_id in by_id:
            raise RuntimeError("action encoder collision")
        by_id[action_id] = spec
        by_source[canonical_json(spec)] = action_id
    return dict(sorted(by_id.items())), by_source


def candidate_id(codec_name: str) -> str:
    canonical = codecs.lookup(codec_name).name
    return opaque_id("c", {"codec": canonical})


def target_id(codec_name: str) -> str:
    canonical = codecs.lookup(codec_name).name
    return opaque_id("t", {"codec": canonical})


def decision_id(source_name: str) -> str:
    return opaque_id("d", {"decision": source_name})


def label_id(source_name: str) -> str:
    return opaque_id("k", {"class": source_name})


def normalize_decoder_state(raw: tuple[bytes, int]) -> tuple[str, int]:
    buffered, flag = raw
    if not isinstance(buffered, (bytes, bytearray)) or not isinstance(flag, int):
        raise TypeError(f"unsupported incremental decoder state {raw!r}")
    return bytes(buffered).hex(), flag


def denormalize_decoder_state(raw: tuple[str, int]) -> tuple[bytes, int]:
    return bytes.fromhex(raw[0]), int(raw[1])


# Internal state key: (phase, steps, buffer_hex, flag). Terminal states keep
# empty buffer/flag values to make serialization uniform.
StateKey = tuple[str, int, str, int]


def initial_state_key(codec_name: str) -> StateKey:
    decoder = codecs.getincrementaldecoder(codec_name)(errors="strict")
    buffer_hex, flag = normalize_decoder_state(decoder.getstate())
    return ("active", 0, buffer_hex, flag)


def state_spec(state: StateKey) -> dict[str, object]:
    phase, steps, buffer_hex, flag = state
    payload: dict[str, object] = {"phase": phase, "steps": steps}
    if phase == "active":
        payload["buffer_hex"] = buffer_hex
        payload["flag"] = flag
    return payload


def state_id(codec_name: str, state: StateKey) -> str:
    # Codec is included only in the hash preimage. It is not emitted in the OIA
    # machine state identifier.
    return opaque_id(
        "s",
        {"codec": codecs.lookup(codec_name).name, "state": state_spec(state)},
    )


def output_token_text(text: str) -> dict[str, object]:
    return {"kind": "text", "codepoints": [ord(char) for char in text]}


def output_id(token: Mapping[str, object]) -> str:
    return opaque_id("o", dict(token))


def source_step(
    codec_name: str,
    state: StateKey,
    action: Mapping[str, object],
    *,
    horizon: int = HORIZON,
) -> tuple[dict[str, object], StateKey]:
    phase, steps, buffer_hex, flag = state

    if phase == "horizon":
        return {"kind": "horizon_exceeded"}, state
    if phase == "error":
        return {"kind": "closed_after_error"}, state
    if phase == "finished":
        return {"kind": "closed_after_finish"}, state
    if phase != "active":
        raise ValueError(f"unknown phase {phase!r}")
    if steps >= horizon:
        terminal = ("horizon", steps, "", 0)
        return {"kind": "horizon_exceeded"}, terminal

    decoder = codecs.getincrementaldecoder(codec_name)(errors="strict")
    decoder.setstate(denormalize_decoder_state((buffer_hex, flag)))
    next_steps = steps + 1

    try:
        if action["kind"] == "finish":
            text = decoder.decode(b"", final=True)
            return output_token_text(text), ("finished", next_steps, "", 0)
        if action["kind"] != "push_byte":
            raise ValueError(f"unknown action kind {action['kind']!r}")
        value = int(action["value"])
        if not 0 <= value <= 255:
            raise ValueError(f"byte value outside range: {value}")
        text = decoder.decode(bytes((value,)), final=False)
    except UnicodeDecodeError:
        # The adapter intentionally normalizes all strict decoding failures and
        # closes the episode. It never relies on decoder state after exception.
        return {"kind": "decode_error"}, ("error", next_steps, "", 0)

    next_buffer, next_flag = normalize_decoder_state(decoder.getstate())
    return output_token_text(text), (
        "active",
        next_steps,
        next_buffer,
        next_flag,
    )


@dataclass(frozen=True)
class AdaptedCodec:
    machine: MealyMachine
    state_manifest: Mapping[str, Mapping[str, object]]
    access_words: Mapping[str, tuple[str, ...]]
    output_manifest: Mapping[str, Mapping[str, object]]


def build_machine(
    codec_name: str,
    *,
    horizon: int = HORIZON,
    actions_by_id: Mapping[str, Mapping[str, object]] | None = None,
) -> AdaptedCodec:
    actions_by_id = actions_by_id or action_encoder()[0]
    canonical_name = codecs.lookup(codec_name).name
    machine_name = candidate_id(canonical_name)
    initial = initial_state_key(canonical_name)
    initial_id = state_id(canonical_name, initial)

    state_by_id: dict[str, StateKey] = {initial_id: initial}
    access_words: dict[str, tuple[str, ...]] = {initial_id: ()}
    transitions: dict[str, dict[str, Transition]] = {}
    output_manifest: dict[str, Mapping[str, object]] = {}
    queue: deque[str] = deque([initial_id])

    while queue:
        current_id = queue.popleft()
        current = state_by_id[current_id]
        by_action: dict[str, Transition] = {}
        for action_id, action in sorted(actions_by_id.items()):
            token, successor = source_step(
                canonical_name, current, action, horizon=horizon
            )
            encoded_output = output_id(token)
            output_manifest.setdefault(encoded_output, dict(token))
            successor_id = state_id(canonical_name, successor)
            if successor_id not in state_by_id:
                state_by_id[successor_id] = successor
                access_words[successor_id] = access_words[current_id] + (action_id,)
                queue.append(successor_id)
            elif state_by_id[successor_id] != successor:
                raise RuntimeError("state encoder collision")
            by_action[action_id] = Transition(encoded_output, successor_id)
        transitions[current_id] = by_action

    state_manifest = {
        opaque: state_spec(state)
        for opaque, state in sorted(state_by_id.items())
    }
    machine = MealyMachine(
        name=machine_name,
        initial_state=initial_id,
        transitions=transitions,
        metadata={
            "adapter": "cpython_incremental_codec_finite_horizon_v1",
            "horizon": horizon,
            "source_kind": "public_executable_substrate",
        },
    )
    return AdaptedCodec(
        machine=machine,
        state_manifest=state_manifest,
        access_words=access_words,
        output_manifest=dict(sorted(output_manifest.items())),
    )


def direct_trace(
    codec_name: str,
    actions: Iterable[Mapping[str, object]],
    *,
    horizon: int = HORIZON,
) -> tuple[tuple[dict[str, object], ...], StateKey]:
    state = initial_state_key(codec_name)
    outputs: list[dict[str, object]] = []
    for action in actions:
        token, state = source_step(codec_name, state, action, horizon=horizon)
        outputs.append(token)
    return tuple(outputs), state


def source_file_record(codec_name: str) -> dict[str, object]:
    canonical = codecs.lookup(codec_name).name
    decoder_cls = codecs.lookup(canonical).incrementaldecoder
    source_path_raw = inspect.getsourcefile(decoder_cls)
    if source_path_raw is None:
        raise RuntimeError(f"no source path for codec {canonical}")
    source_path = Path(source_path_raw)
    data = source_path.read_bytes()
    return {
        "requested_name": codec_name,
        "canonical_name": canonical,
        "module": decoder_cls.__module__,
        "source_path_at_freeze": str(source_path),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_size_bytes": len(data),
    }


def runtime_provenance(codec_names: Iterable[str]) -> dict[str, object]:
    return {
        "python_implementation": sys.implementation.name,
        "python_version": sys.version,
        "python_hexversion": sys.hexversion,
        "cache_tag": sys.implementation.cache_tag,
        "codec_sources": [source_file_record(name) for name in codec_names],
    }
