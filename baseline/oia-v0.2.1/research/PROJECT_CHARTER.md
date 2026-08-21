# OIA-1 Project Charter

## Exact intervention-identifiability auditing for executable candidate systems

**Project class:** separate bounded successor project  
**Charter revision:** 2026-08-21  
**Current implementation:** `ontology-intervention-auditor` v0.2.0

## 1. Purpose

OIA-1 asks whether a declared action/observation interface can adjudicate distinctions among supplied executable candidate models before those distinctions are treated as scientifically recovered or operationally useful.

The motivating failure mode is:

1. several executable hypotheses fit opened histories;
2. a learner or researcher assigns them different structural meanings;
3. further learner work is undertaken; but
4. the permitted interventions never had the power to distinguish the disputed feature, or resolving it could not change a declared decision.

OIA-1 isolates the intervention-identifiability instrument. It is not another ontology learner and does not reopen the prior AOEL implementation ladder.

## 2. Governing question

> For a finite set of deterministic executable candidates, a shared intervention interface, and a predeclared identity, target-class, or decision distinction, can an exact auditor synthesize a guaranteed separating policy, verify a cap-limited policy witness without overstating optimality, or certify exact impossibility after complete closure?

## 3. Core bounded claim

For deterministic, complete, finite Mealy candidates with a common action alphabet:

- complete reachable-belief analysis exactly characterizes finite guaranteed adaptive target identification;
- a complete positive result yields a minimum-worst-case verified policy;
- an incomplete capped positive result may yield a sound witness whose depth is only an upper bound;
- a complete negative result yields a verified closed losing-set certificate;
- cap-limited search never reports impossibility;
- preset identification is separately characterized by partition-state search; and
- finite-horizon decision value can be computed under model-independent or candidate-dependent intervention loss.

All claims concern the supplied candidate set, interface, target, horizon, costs, and utilities.

## 4. Two-track standard

### Track A — opened external instrument validation, authorized now

A numbered Track A audit may use a public, independently authored, licensed, resettable deterministic substrate or a clearly bounded deterministic slice. Iteration is permitted between numbered audits. Before consulting the intervention outcome selected by OIA, each audit freezes:

- candidate set and source provenance;
- adapter boundary and horizon;
- opaque encoder;
- action and observation alphabet;
- target distinction;
- decision criterion and costs;
- caps;
- OIA/adapter source hashes; and
- the prospective execution rule.

Track A may support claims about:

- adapter trace fidelity;
- exactness and cap semantics;
- prospective separator selection within the opened study;
- identity-versus-target/decision efficiency;
- outside-model detection;
- real scaling and instrument failure; and
- behavioral adequacy against direct black-box replay.

Track A cannot support claims of necessary ontology revision, evaluator-private truth recovery, semantic grounding, or decision superiority.

### Track B — sealed confirmation, not authorized

Track B is required for claims that:

- a new ontology concept or rule was necessary;
- evaluator-private interventions identify the author’s latent structure;
- a learned revision transfers to untouched schema-level reserves; or
- ontology-based decisions outperform strong behaviorally adequate black-box or model-free baselines.

Track B retains preregistration, untouched reserves, provenance isolation, evaluator-private outcomes, authoritative utility/safety semantics, leakage audits, strong baselines, and no post-outcome tuning.

## 5. Explicit non-claims

OIA-1 does not claim:

- that any candidate is semantically correct or exhaustive;
- that behavioral equivalence implies semantic equivalence;
- that candidate identifiers or target labels are grounded;
- that a learner can generate the candidates from unfamiliar raw evidence;
- that the author’s ontology is identifiable;
- that arbitrary ontology languages admit finite compilation;
- that the integrated algorithms are individually novel;
- that a Track A outside-model event proves necessary schema revision; or
- that a declared instrument utility is an independently authoritative operational objective.

## 6. Formal input contract

The core accepts:

- finitely many deterministic, input-complete Mealy machines;
- one known initial state per candidate;
- one shared finite action alphabet;
- observable transition outputs;
- optional fixed target labels;
- optional terminal utilities per candidate and decision;
- optional priors;
- optional model-independent action costs; and
- optional candidate-dependent action losses.

Candidate names and metadata are ignored by the algorithms.

## 7. Endpoint vocabulary

1. **Pairwise witness:** shortest fixed action sequence producing different output traces.
2. **Pairwise equivalence:** complete product closure with no mismatch.
3. **Adaptive `solved`:** verified policy plus complete enumeration and certified minimum depth.
4. **Adaptive `witness`:** verified cap-limited policy; reported depth is only a witness upper bound.
5. **Adaptive `impossible`:** verified closed losing set after complete enumeration.
6. **Adaptive `unknown`:** cap interrupted the search before a witness or complete certificate.
7. **Preset `solved`/`impossible`/`unknown`:** shortest sequence, complete no-sequence closure, or cap interruption.
8. **Decision result:** exact finite-horizon expected or maximin policy within the declared value model.

## 8. Decisive implementation falsifiers

The core claim is falsified by a reproducible in-scope case where:

- a reported shortest pairwise separator is non-separating or non-minimal;
- candidates reported equivalent have a finite separator;
- a policy omits an executable output branch or stops at a target-impure belief;
- a `solved` depth is exceeded by a shorter valid policy;
- a `witness` is described as globally minimal;
- a cap-limited run reports impossibility;
- a closed losing-set certificate fails verification;
- a preset minimum is non-minimal; or
- an exact value policy is dominated by an exhaustively enumerated policy within the same horizon.

## 9. Evidence classes

- **E0 — Formal construction:** fixed-point characterization, witnesses, and certificates.
- **E1 — Implementation validation:** deterministic tests, differential oracles, malformed-artifact rejection, and deterministic structural scaling evidence.
- **E2A — Opened external adapter validation:** public substrate, trace-preserving finite adapter, source hashes, and direct black-box replay.
- **E3A — Opened prospective instrument outcome:** pre-outcome frozen policy executed once, including outside-model outcomes.
- **E4B — Sealed necessary-revision/decision confirmation:** not authorized.

Current status: E0, E1, E2A, and one bounded E3A result on CPython incremental codecs. No E4B claim exists.

## 10. Work packages

### WP1 — Exact finite core

Complete in v0.1 and revised in v0.2 to make capped policy witnesses explicit and verifiable.

### WP2 — Independent implementation validation

Complete for the current core: 22 deterministic tests and 1,927 randomized differential checks, plus deterministic scaling-artifact reproducibility.

### WP3A — Public substrate adapter

Complete for one substrate-specific slice: CPython incremental codecs. This is deliberately not a general ontology compiler.

### WP4A — Opened numbered audit

Audit 000 preserved an all-byte scaling noncompletion. Audit 001 closed before outcome after exposing a partition-convergence bug. Audit 002 completed with exact policy synthesis, black-box replay, and a frozen prospective outside-model result.

### WP5B — Sealed confirmation

Not authorized. See `NEXT_EXTERNAL_GATE.md`.

## 11. Stop and revision rules

- Track A failure does not authorize locally generated worlds until something separates.
- Cap-limited noncompletion is recorded as scaling evidence, not impossibility.
- Instrument defects found before outcome close the numbered audit; the corrected instrument proceeds under a new audit number.
- Instrument defects found after outcome invalidate affected claims and must be reported.
- No Track A result may be relabelled as Track B evidence.
