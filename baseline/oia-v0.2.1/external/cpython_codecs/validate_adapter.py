"""Complete reachable-edge trace validation for the codec adapter."""

from __future__ import annotations

import codecs
from typing import Mapping

from codec_adapter import (
    HORIZON,
    AdaptedCodec,
    action_encoder,
    build_machine,
    normalize_decoder_state,
    output_id,
    state_spec,
)


def independent_replay(
    codec_name: str,
    action_ids: tuple[str, ...],
    actions_by_id: Mapping[str, Mapping[str, object]],
    *,
    horizon: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    decoder = codecs.getincrementaldecoder(codec_name)(errors="strict")
    phase = "active"
    steps = 0
    outputs: list[dict[str, object]] = []

    for action_id in action_ids:
        action = actions_by_id[action_id]
        if phase == "horizon":
            outputs.append({"kind": "horizon_exceeded"})
            continue
        if phase == "error":
            outputs.append({"kind": "closed_after_error"})
            continue
        if phase == "finished":
            outputs.append({"kind": "closed_after_finish"})
            continue
        if steps >= horizon:
            phase = "horizon"
            outputs.append({"kind": "horizon_exceeded"})
            continue

        steps += 1
        try:
            if action["kind"] == "finish":
                text = decoder.decode(b"", final=True)
                outputs.append(
                    {"kind": "text", "codepoints": [ord(char) for char in text]}
                )
                phase = "finished"
                continue
            value = int(action["value"])
            text = decoder.decode(bytes((value,)), final=False)
            outputs.append(
                {"kind": "text", "codepoints": [ord(char) for char in text]}
            )
        except UnicodeDecodeError:
            outputs.append({"kind": "decode_error"})
            phase = "error"

    result: dict[str, object] = {"phase": phase, "steps": steps}
    if phase == "active":
        buffer_hex, flag = normalize_decoder_state(decoder.getstate())
        result["buffer_hex"] = buffer_hex
        result["flag"] = flag
    return outputs, result


def validate_one(
    codec_name: str,
    adapted: AdaptedCodec,
    actions_by_id: Mapping[str, Mapping[str, object]],
    *,
    horizon: int,
) -> dict[str, object]:
    machine = adapted.machine
    checked_states = 0
    checked_edges = 0

    for opaque_state, access_word in sorted(adapted.access_words.items()):
        _, reached_spec = independent_replay(
            codec_name, access_word, actions_by_id, horizon=horizon
        )
        expected_spec = dict(adapted.state_manifest[opaque_state])
        if reached_spec != expected_spec:
            raise AssertionError(
                f"state trace mismatch for {codec_name}/{opaque_state}: "
                f"{reached_spec!r} != {expected_spec!r}"
            )
        checked_states += 1

        for action_id, transition in sorted(machine.transitions[opaque_state].items()):
            outputs, successor_spec = independent_replay(
                codec_name,
                access_word + (action_id,),
                actions_by_id,
                horizon=horizon,
            )
            direct_output = output_id(outputs[-1])
            if direct_output != transition.output:
                raise AssertionError(
                    f"output mismatch for {codec_name}/{opaque_state}/{action_id}"
                )
            compiled_successor_spec = dict(
                adapted.state_manifest[transition.next_state]
            )
            if successor_spec != compiled_successor_spec:
                raise AssertionError(
                    f"successor mismatch for {codec_name}/{opaque_state}/{action_id}"
                )
            checked_edges += 1

    return {
        "candidate_id": machine.name,
        "canonical_codec": codecs.lookup(codec_name).name,
        "states_checked": checked_states,
        "edges_checked": checked_edges,
        "result": "pass",
    }


def validate_family(
    codec_names: tuple[str, ...],
    *,
    horizon: int = HORIZON,
) -> tuple[list[AdaptedCodec], dict[str, object]]:
    actions_by_id, _ = action_encoder()
    adapted = [
        build_machine(name, horizon=horizon, actions_by_id=actions_by_id)
        for name in codec_names
    ]
    rows = [
        validate_one(
            name, model, actions_by_id, horizon=horizon
        )
        for name, model in zip(codec_names, adapted, strict=True)
    ]
    return adapted, {
        "validation": "complete_reachable_state_and_edge_replay",
        "independent_replay_path": True,
        "horizon": horizon,
        "action_count": len(actions_by_id),
        "candidate_count": len(codec_names),
        "total_states_checked": sum(int(row["states_checked"]) for row in rows),
        "total_edges_checked": sum(int(row["edges_checked"]) for row in rows),
        "rows": rows,
        "result": "pass",
    }
