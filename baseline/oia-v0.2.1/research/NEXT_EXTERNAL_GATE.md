# Track B External Gate

## Conditions for sealed necessary-revision or decision-superiority claims

OIA-1 v0.2.0 authorizes opened Track A instrument validation. It does **not** authorize sealed Track B claims. This document defines the remaining gate.

## 1. Required substrate and reserves

A Track B proposal must have:

1. an independently authored, licensed, resettable executable substrate;
2. at least two schema-level development families and one untouched schema-level reserve;
3. a learner-visible opaque interface whose fields do not encode source objects, rules, goals, or action semantics;
4. evaluator-private held-out interventions and outcomes; and
5. an immutable source/provenance record for substrate, adapter, candidate generation, audit, and evaluation.

## 2. Necessary-revision endpoint

The study must predeclare a structural inadequacy that cannot be repaired by parameter retuning inside the base representation. A successful endpoint requires all of the following:

- the base candidate class fails a held-out behavioral obligation or returns outside-model;
- a specific new entity/type/property/relation/event/rule construct is proposed without evaluator-private leakage;
- the revised executable candidate class can express the missing behavior;
- evaluator-private interventions distinguish the revision from behaviorally adequate alternatives; and
- the revision transfers to an untouched family or reserve.

An outside-model event alone is insufficient. It demonstrates candidate-family inadequacy for an observation, not which new concept is necessary.

## 3. Decision endpoint

Any decision or safety claim requires externally defined utility/safety signals frozen before outcome inspection. The study must compare against strong alternatives, including as appropriate:

- direct black-box prediction and planning;
- a latent world model with comparable data and compute;
- model-free control;
- robust planning over observed histories without explicit ontology structure; and
- ablations that preserve predictive capacity while removing the claimed structural revision.

The ontology system must improve a predeclared held-out decision metric, not merely produce a more interpretable internal description.

## 4. Leakage controls

The sealed reserve must remain absent from:

- candidate proposal and ranking;
- adapter design beyond the public interface contract;
- target labels and ontology vocabulary;
- stopping thresholds and cap choices;
- decision utilities and safety limits;
- baseline tuning; and
- post-hoc equivalence definitions.

A separate audit must verify this isolation before the reserve is opened.

## 5. Uncertainty and deferral

The protocol must predeclare:

- how multiple surviving candidates are preserved;
- when common-optimal action is accepted;
- when an intervention is selected;
- when the system defers;
- how outside-model observations are handled; and
- how a necessary revision re-enters the version space.

## 6. Pre-outcome artifacts

Before the first sealed outcome, freeze:

- complete protocol and hypotheses;
- candidate and baseline implementations;
- adapter and trace-preservation tests;
- OIA targets, horizon, encoder, costs, and caps;
- all source and dependency hashes;
- evaluation data identifiers;
- random seeds;
- statistical analysis; and
- success, failure, and invalidation rules.

## 7. Authorization rule

Track B remains closed until every item above is satisfied prospectively. A successful Track A audit is evidence that the instrument can operate on a public substrate; it is not sufficient authorization by itself.
