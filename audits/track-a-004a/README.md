# OIA-1 Track A 004a

Track A 004a is the retrospective adapter-integration gate for the two fixed
predictive programs admitted by Track A 003b. It asks whether unchanged accepted
OIA-1 v0.2.1 can consume their bounded behavior and certify a separator.

This is not a prospective discovery experiment. All 84 deterministic action-word
traces per candidate, including the known first divergence, were inspected before
this gate was designed. The strongest allowed success claim is therefore that OIA
independently reconstructs and certifies a minimum separator from a mechanically
compiled, frozen representation.

## Frozen adapter

`ADAPTER_SOURCE_TRACES.json` is a compact, committed projection of the ignored
Track A 003b full-stage evidence. Each projected trace remains bound to the hash
of its original record, whose common P0 is stored once. The compiler requires all
84 words of lengths one through three for each candidate, checks all eight
seed/repetition copies, and rejects prefix-inconsistent traces.

`OIA_INPUT.frozen.json` represents each candidate as a complete deterministic
Mealy machine. States correspond to all 85 observed prefixes (the reset prefix
and 84 nonempty words). A candidate-independent sink makes the input complete
after depth three while emitting only `OBS_BOUNDARY_EXHAUSTED`; it cannot create
a post-envelope distinction. Output tokens are hashes of a fixed observation
projection and are decoded in `OUTPUT_MANIFEST.opened.json`.

The exact protocol, adapter validation, accepted OIA sources, tests, runner, and
verifiers are pinned by `PRE_RUN_SHA256SUMS.txt`. That package must be merged to
protected `main` before `scripts/run_track_a_004a.py` is executed.

During engineering inspection after the first local generation, the accepted
pairwise-separator helper was called once and returned the already-published
`ACTION2` divergence. `ENGINEERING_PRECHECK.pre-full-audit.json` preserves that
ordering correction. No full OIA audit ran, and the package is refrozen before
one does. This further rules out any prospective interpretation but does not
change the retrospective validation endpoint.

## Verification

```bash
python scripts/verify_track_a_004a_prerun.py
python -m unittest tests.test_track_a_004a_adapter -v
```

After an outcome exists, `python scripts/verify_track_a_004a_outcome.py` verifies
its package, serialized adaptive witness, source-trace replay, cross-process
hash record, and a fresh `PYTHONHASHSEED=23` OIA execution.

## Result

The frozen gate passed. Accepted OIA-1 v0.2.1 returned an exact,
enumeration-complete, globally minimum one-step identification policy selecting
`ACTION2`. Report bytes were identical under `PYTHONHASHSEED` 0, 1, 5, and 10;
the independent outcome verifier reproduced them under seed 23. Both policy
branches replayed against the committed source traces.

See [`outcome/RETROSPECTIVE_RESULT.md`](outcome/RETROSPECTIVE_RESULT.md) and the
machine-readable [`outcome/EXECUTION_RECORD.json`](outcome/EXECUTION_RECORD.json).
[`NEXT_GATE.md`](NEXT_GATE.md) distinguishes the recommended new held-out slice
from a lower-cost real-outcome check on this already-known frontier.

## Boundary

This gate executes only the accepted OIA over committed finite machines. It does
not execute a candidate program or ARC environment, make a real ARC action,
contact a model/API/service, use credentials, access private or sealed material,
or support decision-value, ontology-revision, planning-superiority, or Track B
claims.
