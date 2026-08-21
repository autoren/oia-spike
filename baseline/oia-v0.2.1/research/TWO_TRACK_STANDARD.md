# OIA-1 Two-Track Research Standard

**Effective date:** 2026-08-21

## Track A — opened instrument validation

Track A exists to improve and test the OIA instrument incrementally without pretending that an opened development study is sealed confirmation.

A Track A audit must:

1. use a public, licensed, independently authored executable substrate or a clearly bounded deterministic slice;
2. use externally sourced candidate implementations or models rather than a new locally generated ontology ladder;
3. expose an opaque action/output interface to OIA;
4. use the smallest trace-preserving complete or finite-horizon lazy adapter needed for the audit;
5. freeze candidate set, target, horizon, encoder, decision criterion, caps, and instrument source hashes before the OIA-selected outcome is consulted;
6. number every audit and preserve failures, cap noncompletion, and outside-model outcomes;
7. verify adapter traces independently of the compiled transition table; and
8. avoid comparative superiority claims unless an equally resourced behaviorally adequate black-box/non-ontological alternative is included.

Permitted Track A claims:

- adapter fidelity;
- separator/witness correctness;
- exactness or witness-only cap status;
- decision-versus-identity efficiency within the declared candidate set;
- opened prospective separator execution;
- outside-model detection;
- algorithmic and adapter scaling; and
- instrument bugs and negative findings.

Forbidden Track A claims:

- recovery of evaluator-private ontology semantics;
- necessary concept or rule invention;
- sealed held-out generalization;
- independent operational utility/safety value; or
- superiority over strong black-box/model-free alternatives without a proper comparison.

Iteration is allowed **between** numbered audits. Once an outcome has been consulted, the frozen policy and protocol remain immutable for that audit.

## Track B — sealed confirmation

Track B is reserved for claims that a learned executable ontology revision is necessary, externally identified, transferable, or decision-superior.

Before a Track B run, the study must have:

- a preregistered protocol and immutable code/data hashes;
- at least one untouched schema-level reserve;
- evaluator-private interventions and outcomes;
- source/provenance isolation between candidate generation and evaluation;
- authoritative external utility and safety semantics;
- strong black-box, world-model, and model-free baselines as appropriate;
- a necessary-revision criterion that cannot be satisfied by parameter retuning alone;
- predetermined uncertainty, deferral, and outside-model handling;
- a leakage audit; and
- a one-shot outcome rule with no post-outcome tuning.

Track B is not authorized by v0.2.0.

## Relationship between tracks

A positive Track A result can qualify an instrument and expose whether a sealed study is technically plausible. It does not automatically authorize Track B. A negative Track A result can stop or redirect a proposed sealed study before expensive learner work.
