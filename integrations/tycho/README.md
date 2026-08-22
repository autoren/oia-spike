# Tycho causal-trace integration

This is a credential-free, logging-only bridge from the independently qualified
Tycho v0.1 source to the Executable Ontology Lab causal-trace intake contract.
It does not execute Tycho, call a model or service, instantiate ARC, submit an
action or reset, access a private payload, or authorize a protected experiment.

## Exact source

- repository: `https://github.com/NIMI-research/Tycho.git`
- commit: `f68912a764372ead0a610db2e1c011d41ce5197e`
- tree: `d5ff6a4e142934ceb865e403e3aa92d80bfa245c`
- upstream license: Apache-2.0

The parent-project intake contract was frozen at commit
`b6d8d92f4b5106d3ebe28e9998807d3c5d7e8396`, SHA-256
`6219a3a6e7a82fec0620892a426cee2d8daf82adf9cfd2872019a0bb6bab2a2f`.

## Logging delta

`trace-capture-v0.1.patch` adds three fields to Tycho's existing `TraceStep`
when `keep_frames` is enabled:

- `pre_action_frame`;
- every grid in `returned_frames`, including terminal, animation, and
  next-level grids; and
- `available_actions_before`.

The patch changes only `tycho/harness/harness.py` and its existing
action-availability test. It does not change the frame shown to the agent, model
history, tool surface, chosen action, engine call, reset behavior, score, or
resource policy.

Check applicability without changing the pinned checkout:

```bash
python scripts/prepare_tycho_trace_capture.py \
  --repo /path/to/pinned/Tycho --json
```

Apply only in a disposable or evaluator-controlled checkout:

```bash
python scripts/prepare_tycho_trace_capture.py \
  --repo /path/to/pinned/Tycho --apply --json
```

The apply operation is not a run authorization. It leaves the two patched files
as an ordinary uncommitted diff for review.

## Observation export

After an independently authorized run has produced a complete, non-partial
game record with `keep_frames` and schema-2 workspace capture, export its
contract observation stream without importing Tycho or replaying actions:

```bash
python scripts/export_tycho_observation_stream.py \
  --record /path/to/game_record.json \
  --output /path/to/observations.jsonl --json
```

Legacy records without the new fields, partial records, malformed grids,
result frames absent from the returned sequence, non-schema-2 workspaces, and
accidental output overwrites fail closed.

## Validation performed

The patch was independently applied to the exact source pin in a disposable
checkout. Its focused upstream test passed. The complete credential-free Tycho
suite and repository integration suite are required before this integration is
accepted.

This bridge can make a future artifact structurally complete. It cannot turn a
known public run into a prospective discovery result or authenticate evaluator
custody.
