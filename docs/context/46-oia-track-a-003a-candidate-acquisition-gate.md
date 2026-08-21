# OIA Track A 003a — Candidate-Acquisition Gate

**Status:** authorized opened feasibility work  
**Date:** 2026-08-21  
**Accepted instrument baseline:** OIA-1 v0.2.1, commit `3ca35d4`, tag `oia-v0.2.1`  
**Release archive SHA-256:** `2653020afcbf636def260da1517c9e3ba41c2ba1175fc210d4847b303febc33b`

## Purpose

The CPython-codec audit established that the bounded deterministic OIA instrument can operate on one independently authored external substrate. The next unresolved question is not another auditor algorithm. It is whether a source-blind executable-world-model learner can supply a non-circular candidate frontier that OIA can meaningfully audit.

Track A 003a is an acquisition and feasibility audit only. It does not authorize an OIA-selected ARC intervention, a sealed/private evaluation, or a Track B claim.

## Primary question

Can one pinned external learner, starting from the same frozen opened interaction prefix, yield at least two replay-consistent, behaviorally non-equivalent, executable candidate models suitable for a bounded OIA audit?

Two admitted candidates are sufficient for a successful first feasibility result. Three to eight are preferred, not required.

## Preferred first substrate

Use one public ARC-AGI-3 environment only if its SDK, environment artifact, license, reset behavior, observation boundary, and action interface can be pinned reproducibly. Inspect Rodionov's released executable-world-model agent first because it exposes a fixed Python model interface and exact replay machinery. OPINE-World is a secondary option only if its implementation and intermediate candidate artifacts are actually obtainable and pinnable.

Do not assume that either learner exposes a candidate frontier merely because it produces an executable final model. Establish this from code, released artifacts, or a bounded clean-run acquisition test.

## Authorized work

1. Pin official substrate and learner repository commits, releases, dependencies, licenses, and runtime requirements.
2. Inspect public code and released run artifacts for naturally retained alternative programs or checkpoints.
3. Define one opened prefix and a candidate-admission rule before inspecting OIA separability.
4. Determine whether fixed candidate programs can be obtained through released artifacts or bounded clean processes.
5. Record compute, model/API, credential, and cost requirements before any run that would consume paid or scarce resources.
6. Characterize a candidate-independent finite action boundary and a small prospective horizon, without yet building the full adapter.
7. Preserve negative findings and every attempted or rejected candidate source.

Paid model runs, private evaluation, and real prospective environment actions require separate explicit authorization. Public-source inspection and non-mutating local feasibility checks do not.

## Candidate-admission requirements

An admitted candidate must:

- originate from the pinned external learner, not from human-authored challenger semantics;
- be generated or retained independently of how easily OIA separates it;
- exactly replay the same frozen opened prefix at the public observation boundary;
- be a fixed executable artifact during the audit, with no LLM or external service calls during OIA execution;
- expose deterministic, resettable transition behavior over the proposed bounded horizon;
- use the same candidate-independent finite action interface;
- include complete generator, prompt, model, runtime, seed where meaningful, prefix, dependency, and file-hash provenance; and
- remain behaviorally distinct from at least one other admitted candidate after exact bounded deduplication.

Multiple runs of one learner are separately sampled candidates, not independently authored candidates. Any public-game contamination or source-access risk must be recorded and limits the result to opened Track A evidence.

## Feasibility checks

Before adapter construction, establish:

- whether the learner emits one committed model or preserves alternatives;
- whether identical-prefix clean runs can be reproduced sufficiently to freeze artifacts;
- whether model state can be initialized after the prefix without hidden conversation or service state;
- whether direct candidate execution is deterministic;
- whether animations, multi-frame transitions, terminal signals, and errors can be canonically serialized;
- whether parameterized actions, including clicks, can be reduced to a predeclared finite candidate-independent set without semantic leakage; and
- whether a horizon-bounded lazy expansion can distinguish horizon exhaustion from a search cap or unsupported behavior.

## Required result vocabulary

Track A 003a may report:

- `candidate_frontier_feasible`;
- `single_model_only`;
- `no_behavioral_divergence`;
- `replay_failure`;
- `nondeterministic_candidate`;
- `state_initialization_blocker`;
- `action_boundary_blocker`;
- `provenance_or_license_blocker`;
- `resource_authorization_required`; or
- `unknown`.

It must not report global equivalence, global impossibility, necessary ontology revision, autonomous ontology invention, or intervention superiority.

## Deliverables

Produce a concise acquisition report containing:

1. substrate and learner selection with exact provenance;
2. complete attempt and rejection registry;
3. frozen-prefix proposal and evidence that it is opened;
4. candidate artifacts and hashes, if acquired;
5. exact replay and bounded behavioral-deduplication results;
6. deterministic/reset/state-initialization findings;
7. proposed finite action boundary and horizon;
8. compute, credential, model, API, and estimated cost requirements;
9. a pass, blocker, or authorization-required verdict; and
10. the remaining Track A/Track B claim boundary.

## Next authorization boundary

If Track A 003a passes, the next phase may build and exhaustively trace-test the minimum ARC-specific horizon-bounded lazy adapter. It still must not execute an OIA-selected real-environment intervention until candidates, target, encoder, action boundary, horizon, caps, comparator rules, and policy have been frozen.

If Track A 003a fails, preserve the failure as a research result and address only the localized candidate-source, provenance, reset, action-boundary, or resource problem. Do not make OIA the candidate generator merely to force the gate to pass.
