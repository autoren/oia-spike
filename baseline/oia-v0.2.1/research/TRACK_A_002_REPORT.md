# OIA-1 v0.2 Track A Research Report

## Opened external instrument validation on CPython incremental codecs

**Date:** 2026-08-21  
**Completed audit:** `OIA-1-TRACK-A-002`  
**Claim class:** Track A opened instrument validation only

## 1. Result in one paragraph

OIA-1 was revised to distinguish sealed confirmation from incremental opened instrument research. Two v0.1 integrity defects were repaired: adaptive cap-limited policy witnesses now have an explicit non-optimal `witness` status, and structural scaling evidence no longer contains nondeterministic wall-clock values. A substrate-specific finite-horizon adapter was then built for five public CPython incremental decoders. Independent replay verified all 90 reachable adapted states and all 630 transitions. Before the prospective target was executed, OIA exactly synthesized a minimum-worst-case adaptive full-identity policy of depth 3 over 75 reachable beliefs; the predeclared two-class routing decision required only one action. Direct reset-and-query replay followed every selected policy path correctly. The frozen policy was then executed once on the predeclared outside-family decoder `cp437`; its first observation was absent from every frozen candidate branch, so OIA returned `outside_model` at step 1. This validates the bounded instrument path. It does not establish ontology invention, necessary ontology revision, evaluator-private identification, or decision superiority.

## 2. Two-track standard

**Track A**, used here, permits opened iteration between numbered audits on public independently authored executable substrates. The permitted claims are adapter fidelity, exact/cap behavior, separator execution, decision-versus-identity efficiency, outside-model detection, scaling, and other instrument-validation results.

**Track B** remains closed. Necessary ontology revision, evaluator-private identification, transfer to sealed reserves, and decision superiority still require preregistration, untouched reserves, leakage isolation, authoritative outcome/utility semantics, and strong behaviorally adequate black-box/model-free baselines.

## 3. v0.1 integrity repairs

### 3.1 Adaptive cap semantics

The previous documentation said every adaptive cap returned `unknown`, but the algorithm could soundly find a complete policy tree before reachable-belief enumeration finished. v0.2 makes the distinction explicit:

| Status | Enumeration | Artifact | Meaning of `worst_case_steps` |
|---|---:|---|---|
| `solved` | complete | verified policy | certified global minimum |
| `witness` | incomplete/capped | verified policy | verified witness depth only; upper bound on the unknown minimum |
| `impossible` | complete | verified closed losing set | not applicable |
| `unknown` | incomplete/capped | none | no depth claim |

The verifier rejects inconsistent combinations of status, `exact`, `enumeration_complete`, `optimality_certified`, and `depth_claim`. A cap-limited run can never return impossibility.

### 3.2 Reproducible scaling evidence

`research/scaling_probe.py` now writes only deterministic structural outputs. Local wall-clock measurements are console-only lines prefixed `TIMING_LOCAL`. Two consecutive runs produced the same artifact hash:

```text
78b73bf5faf5b21f7d57a5c40cabab883d306399583a1b82817eea491554d2b0  research/scaling_probe_results.json
```

## 4. Public substrate and provenance

### 4.1 Source screen

The first preferred option was the public Automata Wiki/AALpy MQTT Mealy-model family because it offered shared-alphabet models of independently implemented protocol systems. Its exact model archive/source files could not be materialized reproducibly in this execution runtime, so no MQTT bytes or outcomes were used. That acquisition failure is retained in `audit_002/source_screening.json` rather than silently substituting an unfrozen reconstruction.

The selected fallback was the incremental decoder registry supplied by the installed CPython runtime. The substrate is deterministic, resettable, stateful, public, and licensed. Python documents incremental decoder state, reset, finalization, `getstate`, and `setstate` behavior at <https://docs.python.org/3/library/codecs.html>. Python software and documentation are licensed under the Python Software Foundation License Version 2; the authoritative license page is <https://docs.python.org/3/license.html>.

### 4.2 Frozen runtime

```text
implementation: CPython
version:        3.13.5 (main, Jul 15 2026, 20:25:40) [GCC 14.2.0]
cache tag:      cpython-313
```

Candidate family:

| Candidate requested name | Canonical codec | Source module | Source SHA-256 |
|---|---|---|---|
| `utf-8` | `utf-8` | `encodings.utf_8` | `ba0cac060269583523ca9506473a755203037c57d466a11aa89a30a5f6756f3d` |
| `utf-8-sig` | `utf-8-sig` | `encodings.utf_8_sig` | `1ef3da8d8aa08149e7f274dc64dbfce2155da812e5258ca8e8f832428d3b5c2d` |
| `latin-1` | `iso8859-1` | `encodings.latin_1` | `b75503e532a27c636477396c855209ff5f3036536d2a4bede0a576c89382b60c` |
| `cp1252` | `cp1252` | `encodings.cp1252` | `19aa5bee667f5fb387924a813aec9fa1dda47769d09e8483a748bdb202be6a84` |
| `iso8859-15` | `iso8859-15` | `encodings.iso8859_15` | `01976a81811873dc9a0c79db9fc00d1c30103487f3c6bc3a6d81b4043cd48e02` |

The prospective outside-family target was frozen as `cp437`, source module `encodings.cp437`, SHA-256 `5c2a5015cd36cf7f561269f33dec4c323093d3d88b0673969accdabdcb9ce2cb`.

No CPython source files are redistributed. Full paths, sizes, names, and hashes are in `audit_002/source_provenance.json`.

## 5. Adapter boundary and trace preservation

The adapter is `cpython_incremental_codec_finite_horizon_v1`. It is deliberately substrate-specific and is not a general AOEL or ontology compiler.

Frozen boundary:

- **reset:** instantiate a fresh strict incremental decoder;
- **actions:** push one frozen diagnostic byte or explicitly finish;
- **diagnostic bytes:** `0x41`, `0x80`, `0xA4`, `0xBB`, `0xBF`, `0xEF`;
- **horizon:** four actions;
- **outputs:** Unicode codepoint vector, normalized `decode_error`, `closed_after_error`, `closed_after_finish`, or `horizon_exceeded`;
- **error rule:** the first strict `UnicodeDecodeError` closes the episode;
- **completion:** explicit error, finish, and horizon sinks make every adapted machine finite and action-complete;
- **opacity:** SHA-256-derived identifiers hide candidate, action, state, output, target-class, and decision names from OIA.

An independent replay path recreated a fresh decoder from each state’s access word, checked the reconstructed decoder state, then replayed every outgoing action. It did not trust the compiled transition target.

| Candidate | Reachable states checked | Edges checked | Result |
|---|---:|---:|---|
| `utf-8` | 30 | 210 | pass |
| `utf-8-sig` | 30 | 210 | pass |
| `latin-1` | 10 | 70 | pass |
| `cp1252` | 10 | 70 | pass |
| `iso8859-15` | 10 | 70 | pass |
| **Total** | **90** | **630** | **pass** |

## 6. Preserved pre-outcome negatives

### Audit 000 — all-byte scaling noncompletion

The first adapter-validation attempt used all 256 one-byte actions plus `finish` at horizon 4 and required complete reachable-state/edge replay. It did not complete inside the 120-second engineering cap. No audit artifact or identifiability conclusion was accepted. Audit 001 instead froze a seven-action diagnostic alphabet.

### Audit 001 — instrument convergence failure

The first diagnostic audit froze its candidate set and protocol, then the full OIA report failed to complete inside a 120-second execution cap before the prospective target was run. Diagnosis showed that behavioral partition refinement had reached a stable partition but globally renumbered block IDs. Exact mapping comparison therefore never recognized convergence.

The fix refines inside each old block and stops when no old block splits, independent of block-ID numbering. A regression test executes the external codec partition. Audit 001 was closed with `prospective_target_executed=false`; its original freeze and closure manifests are preserved. Audit 002 was newly numbered and refrozen with the corrected instrument source hashes.

## 7. Frozen audit 002 protocol

The following were fixed before OIA selection or target execution:

- five candidates listed above;
- seven-action opaque alphabet;
- horizon 4;
- full candidate identity as the primary target;
- a two-class target/decision: streaming multibyte path versus single-byte path;
- uniform candidate priors;
- utility 1 for the candidate-assigned path and 0 for the other;
- action cost 0.01;
- `max_beliefs=500000`;
- `max_partitions=500000`;
- `value_depth=4`;
- `max_task_loss_frontier=50000`;
- SHA-256 encoder and sidecar mapping;
- all core, adapter, verifier, execution, and regression-test source hashes;
- `cp437` as the outside-family target; and
- the rule to return `outside_model` immediately when a prospective observation has no policy branch.

The opaque audit input and protocol hashes were:

```text
95c85c8f908007ca6b6ecbab58e4e22372d0d42bc7c9d9f4292bb605be4c4428  audit_input.opaque.json
831cb36052e56c2deac74ab6015023f69674155b652e7e30f283505cdba9a3e2  audit_protocol.frozen.json
```

## 8. Pre-outcome OIA result

### 8.1 Behavioral identification

All five initial candidates occupied singleton exact behavioral-equivalence classes. Every pair had a finite separator.

The full adaptive identity result was:

```text
status:                 solved
exact:                  true
enumeration_complete:   true
optimality_certified:   true
depth_claim:            minimum
reachable_beliefs:      75
minimum worst-case:     3 actions
expected path length:   2.4 actions under uniform priors
```

The full **preset** identity endpoint was exactly impossible after complete closure over 138 partition states. Thus this finite slice supplied a genuine adaptive-versus-preset separation: an output-contingent tree identifies all candidates, but no one fixed action word does.

### 8.2 Decision versus identity

The predeclared two-class target and common-optimal routing decision were both exactly identifiable in one action over 38 reachable beliefs. Full identity therefore required two additional worst-case actions:

```text
full identity minimum worst case: 3
decision-class minimum worst case: 1
difference:                        2 actions
```

Under the declared instrument-only utility, the expected finite-horizon value rose from 0.60 without probing to 0.99 after one 0.01-cost action; the robust value rose from 0 to 0.99. These are properties of the supplied routing utility, not an external operational-value or superiority claim.

### 8.3 Exactness and caps

The primary and decision searches terminated far below `max_beliefs=500000`, so their minima are exact rather than cap-limited witnesses. Preset identity also completed far below `max_partitions=500000`, so its impossibility conclusion is exact. No cap-limited impossibility was returned.

## 9. Black-box/non-ontological comparison

A direct reset-and-query codec-oracle baseline replayed the frozen adaptive policy without reading any compiled candidate state. All five candidate traces reached the correct singleton leaf; maximum path length was 3. This establishes behavioral adequacy of the adapter/policy combination against the source implementations.

The baseline did not select the separator and no superiority claim is made. It is a fidelity comparison, not evidence that explicit ontology candidates outperform a black-box system.

## 10. Prospective opened outcome

After `PRE_OUTCOME_SHA256SUMS` was written and verified, the exact primary policy was executed once on the predeclared `cp437` target.

The root action corresponded, in the opened sidecar, to pushing byte `0xEF`. The target returned Unicode codepoint `8745` (`U+2229`, intersection). Its opaque observation was absent from both candidate branches at that policy node.

```text
outcome_status:          outside_model
steps_executed:          1
pre_outcome_verified:    true
post_outcome changes:    0
```

This is a successful outside-model detection for the frozen candidate family and interface. It does **not** show which representation extension is necessary. In particular, it does not by itself justify a new entity, property, relation, event, or rule construct.

## 11. What was learned

1. **The two-track standard is workable.** Opened external iteration exposed real instrument defects without being misreported as sealed confirmation.
2. **Witness validity and optimality must be separate API claims.** A capped policy can be sound even when its depth is not known to be minimum.
3. **Trace-preserving external adaptation can be small and specific.** No AOEL compiler was needed for this slice.
4. **Exact target/decision identification can be much cheaper than exact identity.** Here it was one action versus a worst-case three.
5. **Adaptive experiments can be strictly more capable than preset experiments.** Full adaptive identity was solvable while preset identity was exactly impossible.
6. **Outside-model behavior can be detected prospectively.** The predeclared outside target left the frozen policy tree immediately.
7. **External execution is valuable for instrument debugging.** The codec family exposed a partition-convergence defect not caught by the original randomized suite.
8. **Scaling remains a material boundary.** Full 256-byte edge replay exceeded the engineering cap, even though the seven-action slice was small and exact.

## 12. Remaining claim boundary

The package still does not demonstrate:

- candidate generation from opaque unfamiliar histories;
- ontology or concept invention;
- a necessary structural revision after outside-model evidence;
- recovery of author-intended semantics;
- evaluator-private identification;
- transfer to an untouched schema-level reserve;
- authentic operational utility/safety value; or
- superiority over equally resourced black-box, world-model, or model-free baselines.

Those are Track B questions and remain unauthorized.

## 13. Commands and tests

The exact transcript is in `research/VALIDATION_TRANSCRIPT_V0.2.txt`. Primary commands were:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .

python -m unittest discover -s tests -v
python research/randomized_validation.py
python research/task_loss_validation.py
python research/scaling_probe.py
python research/scaling_probe.py

python external/cpython_codecs/validate_adapter.py
python external/cpython_codecs/prepare_audit.py
python external/cpython_codecs/run_opened_audit.py
python external/cpython_codecs/execute_prospective_outcome.py

sha256sum -c SHA256SUMS
(cd external/cpython_codecs/audit_001 && sha256sum -c FREEZE_SHA256SUMS)
(cd external/cpython_codecs/audit_001 && sha256sum -c AUDIT_CLOSURE_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c FREEZE_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c PRE_OUTCOME_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c FINAL_SHA256SUMS)
```

Validation totals:

| Test family | Count/result |
|---|---:|
| Deterministic tests | 22 pass |
| Random pairwise checks | 1,027 pass |
| Random adaptive checks | 200 pass |
| Random preset checks | 200 pass |
| Random Bayesian task-loss checks | 250 pass |
| Random robust task-loss checks | 250 pass |
| Total randomized differential checks | 1,927 pass |
| External adapter states/edges | 90 / 630 pass |
| Direct black-box candidate paths | 5 pass |

## 14. Integrity manifests and principal checksums

Complete per-file checksums are contained in the manifests; the principal manifest and result hashes are:

```text
3d1bd46cd152688ac79bad627baff05d4403ae687ac1b209f66a35c4f07bf54e  audit_001/FREEZE_SHA256SUMS
945298fd5abdbf2317206187195654a2fdf769e4efa828ef3614f88d39055b9e  audit_001/AUDIT_CLOSURE_SHA256SUMS
35f0a96605d70d82fe3dae2a94dc4954044c6b30a153a4f9d5e515527289db30  audit_001/instrument_failure.pre_outcome.json
8b75abe8c474d9f75d9b4c196a51b11e511713d4970fa327b6a2cf23f7ac5e5f  audit_002/FREEZE_SHA256SUMS
ec74664c7fc3e1a3a311789bc91fcbbcd09de2ed1d94989df08f9a5973371489  audit_002/PRE_OUTCOME_SHA256SUMS
6d475b3728a1db1f18dd740a4014906e466b9f08c74740cc37cecedcf59f7e2a  audit_002/FINAL_SHA256SUMS
b80b103f548890bf62650a5f9756787e1cf083903845a807a6b0144be7b93f9d  audit_002/adapter_trace_validation.json
10bbdb8151be0b073a76a2faa4cdb8083a992aed3820977c17193a40fbe5f2ce  audit_002/oia_report.json
8c5713909efa57b039788a385a1202eb622dd84e0778026872281206485e01c7  audit_002/blackbox_comparison.json
ea9c3fe5d18a4dc2571efc6f2c4369fcc8cf799dbf0e67c30ba780363ca16982  audit_002/selection_record.pre_outcome.json
3ad0fb8e9969056da81c5a78c1825fdc170a2eff1d6544ef5f961a81f95f927c  audit_002/prospective_outcome.json
cd7df5925c72c89e42f13ab237cc5fdffbd3a98f6c0346d7c5cde7e6455d7681  audit_002/instrument_source_provenance.json
22f1880f15a6182a85e38289f5ca3c4a48f8f66daaac3b92a278e0c6eec704c6  audit_002/source_provenance.json
78b73bf5faf5b21f7d57a5c40cabab883d306399583a1b82817eea491554d2b0  research/scaling_probe_results.json
```

The package-level `SHA256SUMS` and archive SHA-256 are generated only after all documentation and transcripts are finalized.
