# DiscoverPhysics context-complete adapter

This integration is a credential-free, execution-free bridge for a possible
prospective DiscoverPhysics-style study. It addresses one specific defect found
in the pinned public source: an experiment can vary absolute `start_time`, but
the current submitted-law signature and generic evaluator do not pass that
context to the executable artifact.

The adapter contract therefore requires the intervention context to flow
unchanged through experiment request, observation, artifact invocation, and
evaluation. It also defines an evaluator-held matched-pair commitment and a
complete ordered trace. Missing context, multiple changes in a purported
matched pair, private truth in learner-visible records, partial ordering, or a
time-blind submitted artifact all fail closed. Pair commitments include a
custodian-held random nonce; a plain hash of the small, predictable phase-pair
space would not be hiding.

## Boundary

This integration does not import or modify DiscoverPhysics, run its simulator,
call a model or service, execute a candidate law, open a private world, score an
outcome, or authorize a prospective episode. It establishes at most that a
context-complete adapter can be validated locally.

The exact public source pin is:

- repository: `https://github.com/SampsonML/DiscoverPhysics.git`;
- commit: `33b7fa9df96de9c35744efd181ca7e5a8dd60ad5`;
- tree: `68cb921b1c7347e78161622fb44194c7fa6d16b3`; and
- license: MIT.

The governing parent analysis is pinned to Executable Ontology Lab commit
`863ea9bd23e029539acb38bedb414a5d9cc8bba2` and its exact document and panel
hashes are recorded in `CONTEXT_ADAPTER_CONTRACT.json`.

## Required artifact interface

An oscillator-like candidate must accept:

```python
def discovered_law(pos1, pos2, p1, p2, velocity2, start_time, duration):
    ...
```

An equivalent structured context object is possible only under a separately
frozen contract that gives it identical semantics and serialization. Silently
defaulting `start_time` to zero is not compatible.

## Utilities

`context_adapter.py` provides pure validation and packaging functions:

- `validate_contract` checks the source, interface, custody, execution, and
  claim boundaries;
- `build_candidate_call` constructs one context-complete evaluator invocation;
- `commit_matched_pair` validates a pair that differs only in `start_time` and
  returns a nonce-hardened canonical SHA-256 commitment without disclosing the
  pair or nonce; and
- `validate_trace` checks complete event ordering, request/observation context
  linkage, resource accounting, hypotheses, and artifact-interface
  preservation.

Run the integration verifier with:

```bash
python scripts/verify_discoverphysics_context_adapter.py
```

No command in this integration executes a learner, simulator, or candidate.
