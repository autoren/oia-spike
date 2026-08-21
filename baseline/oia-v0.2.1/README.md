# Ontology Intervention Auditor

**Version:** 0.2.1  
**Status:** exact bounded research instrument; historical Track A audit preserved with a reproducibility maintenance correction  
**Date:** 2026-08-21

OIA-1 audits a prerequisite that should be checked before a learner is credited with recovering or revising an ontology:

> Given a frozen set of executable candidates and a frozen intervention interface, which candidate or decision distinctions can the interface actually force into observably different behavior?

The core accepts deterministic, complete, finite Mealy machines with a shared action alphabet. It computes behavioral equivalence, pairwise separators, adaptive and preset identification policies, decision-region identification, and finite-horizon intervention value. It does **not** invent candidates or establish that their semantics match an external author’s ontology.

## Two-track research standard

OIA-1 now separates incremental instrument research from sealed confirmation.

### Track A — authorized

Opened validation may iterate between numbered audits on public, independently authored, licensed executable substrates. Claims are restricted to:

- adapter fidelity and opaque-interface preservation;
- prospective separator selection within the opened study;
- identity-versus-target/decision efficiency;
- outside-model detection;
- exactness and cap behavior;
- real scaling and instrument-failure findings; and
- behaviorally adequate black-box replay checks.

Track A does not establish necessary ontology revision, recovery of an evaluator-private truth, or decision superiority.

### Track B — not authorized

Sealed claims retain strict preregistration, untouched reserves, evaluator-private interventions, leakage isolation, necessary-revision tests, and strong black-box/model-free comparisons. See `research/TWO_TRACK_STANDARD.md` and `research/NEXT_EXTERNAL_GATE.md`.

## Exact adaptive status contract

Adaptive synthesis has four mutually exclusive statuses:

| Status | Meaning |
|---|---|
| `solved` | Reachable-belief enumeration completed. The policy is verified and `worst_case_steps` is the certified global minimum. |
| `witness` | A cap-limited search found a verified terminating policy before enumeration completed. `worst_case_steps` is only the witness depth—an upper bound on the unknown minimum. |
| `impossible` | Complete enumeration produced a verified closed losing-set certificate. This status is never returned from a cap-limited search. |
| `unknown` | A cap stopped the search before either a sound policy witness or a complete impossibility certificate was available. |

Every serialized result includes `enumeration_complete`, `optimality_certified`, and `depth_claim`. The verifier rejects contradictory metadata. Preset and task-loss searches still return `unknown` when their own caps prevent a complete endpoint.

## What the core computes

For a finite candidate set with one shared action alphabet, OIA-1 can:

- compute exact behavioral-equivalence classes;
- find shortest pairwise separating intervention sequences;
- synthesize a minimum-worst-case adaptive policy for full identity or any predeclared target class;
- return a verified cap-limited adaptive witness without overstating optimality;
- find a shortest preset sequence or prove preset impossibility by complete closure;
- return a closed losing-set certificate for exact adaptive impossibility;
- determine whether a target label cuts across a behavioral-equivalence class;
- find the minimum probe needed to reach a common-optimal decision; and
- compute exact depth-bounded Bayesian and maximin policies with scalar or candidate-dependent intervention loss.

## Track A audit 002: CPython incremental codecs

The revised package includes one complete opened external instrument-validation slice in `external/cpython_codecs/audit_002/`.

**Substrate.** Public CPython incremental decoder implementations from the frozen CPython 3.13.5 runtime, under the Python Software Foundation License Version 2. The adapter uses the documented reset/stateful decoder interface but is specific to this substrate; it is not an AOEL compiler.

**Candidates.** `utf-8`, `utf-8-sig`, `latin-1`, `cp1252`, and `iso8859-15`. OIA sees only hashed candidate, state, action, output, class, and decision identifiers.

**Frozen interface.** Six one-byte pushes (`0x41`, `0x80`, `0xA4`, `0xBB`, `0xBF`, `0xEF`) plus explicit `finish`, with horizon 4. Strict decoding errors are normalized and close the episode.

**Adapter fidelity.** Independent fresh-decoder replay checked every reachable adapted state and transition: 90 states and 630 edges, all passing.

**Pre-outcome OIA result.** Full adaptive identity was exact with minimum worst-case depth 3 over 75 reachable beliefs. The predeclared two-class routing decision was exact at depth 1 over 38 reachable beliefs. No finite preset sequence could identify all five candidates; preset closure was exact after 138 partition states. Direct reset-and-query black-box replay followed every selected policy branch correctly for all five candidates.

**Prospective opened outcome.** The predeclared outside-family target `cp437` was executed once after the pre-outcome manifest was frozen. The first selected action produced an observation absent from every candidate branch, so the frozen policy returned `outside_model` at step 1. No post-outcome policy changes were made.

These are Track A instrument results only. They do not show ontology invention, necessary revision, semantic grounding, or operational decision superiority.

## v0.2.1 reproducibility maintenance

Independent verification found that v0.2.0 serialized one internal equal-depth policy tie according to Python set iteration order. Both observed policies were verified exact depth-3 optima, and the root selection, exact depth, decision result, black-box replay, and opened `cp437` outcome were unchanged.

v0.2.1 separates rank construction from policy canonicalization. Reachable beliefs are processed in canonical order, and after the final rank map is known the lexicographically smallest action is selected among all actions attaining the minimum rank. Fresh processes under `PYTHONHASHSEED=0,1,2,5,10,42,123` now produce one report hash and one policy hash:

```text
report SHA-256: 10bbdb8151be0b073a76a2faa4cdb8083a992aed3820977c17193a40fbe5f2ce
policy SHA-256: 612c0572b8f04a4fd3ff82ef2f33f198cda6442200ca7876f24deb6cd3918799
```

The report remains byte-for-byte identical to the historical stored report. This maintenance did not rerun the codec substrate or the `cp437` outcome. See `research/V0.2.1_MAINTENANCE_REPORT.md`.

## Preserved negative results

The package keeps three material negatives:

1. **Audit 000 scaling negative:** complete edge replay for all 256 one-byte actions plus `finish` did not complete inside the 120-second engineering cap. It was narrowed to a predeclared diagnostic alphabet rather than silently treated as success.
2. **Audit 001 instrument failure:** the first frozen diagnostic audit exposed a partition-refinement termination defect. A stable partition was repeatedly renumbered, preventing completion. The prospective target was not executed. The defect, pre-fix hash, corrected hash, and closure manifest are retained in `external/cpython_codecs/audit_001/`.
3. **Public MQTT family acquisition failure:** Automata Wiki/AALpy MQTT models were screened first, but their exact source artifacts could not be materialized reproducibly in this runtime, so they were not used. The screen is recorded in `audit_002/source_screening.json`.

## Integrity repair: deterministic scaling evidence

`research/scaling_probe.py` now writes only deterministic structural values to `research/scaling_probe_results.json`. Wall-clock measurements are printed with a `TIMING_LOCAL` prefix and never enter the checksummed artifact. Two consecutive runs produced the same file hash:

```text
78b73bf5faf5b21f7d57a5c40cabab883d306399583a1b82817eea491554d2b0
```

## Install and run

The package requires Python 3.11 or newer and has no runtime dependencies.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
ontology-auditor examples/pilot_instance.json
```

Run the core validation suite:

```bash
python -m unittest discover -s tests -v
python research/randomized_validation.py
python research/task_loss_validation.py
python research/scaling_probe.py
python research/hash_seed_reproducibility.py
python maintenance/verify_provenance.py
```

Revalidate the adapter without re-executing the prospective target:

```bash
PYTHONPATH=src:external/cpython_codecs python - <<'PY'
import json
from pathlib import Path
from codec_adapter import CANDIDATE_CODECS, HORIZON
from validate_adapter import validate_family
_, result = validate_family(CANDIDATE_CODECS, horizon=HORIZON)
frozen = json.loads(Path(
    "external/cpython_codecs/audit_002/adapter_trace_validation.json"
).read_text())
assert result == frozen
print(result["total_states_checked"], result["total_edges_checked"])
PY
```

`prepare_audit.py` refuses to overwrite audit 002 after an outcome exists. The original v0.2.0 `run_opened_audit.py` is retained byte-for-byte both at its live path and in the historical source snapshot; but its historical source check now fails closed against the corrected current tree before any write because `synthesis.py` has a different hash. Current maintenance replay is performed only by `research/hash_seed_reproducibility.py`, which consumes the frozen opaque machine input without invoking any codec implementation or `cp437`. The delivered `audit_002` contains the single prospective outcome; `execute_prospective_outcome.py` was not run during maintenance and must not be presented as a fresh prospective test.

Verify package and audit integrity:

```bash
sha256sum -c SHA256SUMS
python maintenance/verify_provenance.py
(
  cd external/cpython_codecs/audit_001
  sha256sum -c FREEZE_SHA256SUMS
  sha256sum -c AUDIT_CLOSURE_SHA256SUMS
)
(
  cd external/cpython_codecs/audit_002
  sha256sum -c FREEZE_SHA256SUMS
  sha256sum -c PRE_OUTCOME_SHA256SUMS
  sha256sum -c FINAL_SHA256SUMS
)
```

## Validation inventory

- 23 deterministic tests, including adaptive cap semantics, external partition convergence, and a cross-process hash-seed regression;
- 1,027 randomized pairwise separator/equivalence checks;
- 200 randomized adaptive-depth checks;
- 200 randomized preset checks;
- 250 randomized Bayesian task-loss checks;
- 250 randomized robust task-loss checks;
- deterministic scaling artifact rerun stability;
- one serialized audit report and policy hash across seven fresh `PYTHONHASHSEED` values;
- 90 external adapted states and 630 external edges replayed independently; and
- five direct black-box policy paths replayed successfully.

The 1,927 randomized checks and local examples validate the implementation on generated cases. The CPython slice adds opened external instrument evidence, not a sealed ontology-identification result.

## Package map

- `src/ontology_auditor/` — exact finite core and verifiers.
- `tests/` — deterministic unit and Track A regression tests.
- `examples/` — small synthetic demonstrations.
- `external/cpython_codecs/` — substrate-specific adapter, validation scripts, numbered audits, and manifests.
- `research/TRACK_A_002_REPORT.md` — original v0.2.0 Track A report, retained as historical evidence.
- `research/V0.2.1_MAINTENANCE_REPORT.md` — deterministic tie-break and provenance correction.
- `maintenance/` — explicit historical/current provenance map, current-source manifest, and verifier.
- `historical/` — byte-identical v0.2.0 release archive, original instrument-source snapshot, and explicit path-resolution notes.
- `research/FORMAL_SPEC.md` — exact characterizations and cap vocabulary.
- `research/TWO_TRACK_STANDARD.md` — authorization and claim boundaries.
- `research/VALIDATION_TRANSCRIPT_V0.2.txt` — historical v0.2.0 commands and frozen outputs.
- `research/VALIDATION_TRANSCRIPT_V0.2.1.txt` — maintenance validation commands and outputs.
- `SHA256SUMS` — complete package file manifest.

## Non-claims

OIA-1 does not claim that:

- any supplied candidate is semantically correct or complete;
- behavioral equivalence implies semantic equivalence;
- a learner can invent these candidates from raw unfamiliar experience;
- the author’s latent ontology has been identified;
- a general ontology language can be compiled into this finite interface;
- the prospective `cp437` result constitutes necessary schema revision;
- the routing utility is an independently authoritative operational objective; or
- explicit candidates outperform an equally resourced black-box or model-free controller.

## License

OIA-1 code and documentation are MIT licensed. The package does not redistribute CPython source files; it records source paths and SHA-256 provenance for the externally executed codec implementations. See `THIRD_PARTY_NOTICES.md`.
