# Research Note: Exact Intervention-Identifiability Auditing Under a Two-Track Standard

**Project:** OIA-1  
**Version:** 0.2.0  
**Date:** 2026-08-21

## Abstract

OIA-1 addresses a recurring failure mode in executable ontology research: investing in candidate generation or revision before establishing that the permitted intervention interface can adjudicate the proposed distinction. Given a finite set of deterministic executable candidates, OIA-1 computes exact behavioral equivalence, pairwise separators, adaptive and preset target policies, decision-region identification, and finite-horizon intervention value. Positive and negative artifacts are independently executable or verifiable.

Version 0.2 introduces a two-track standard. Track A permits opened instrument validation on public independently authored substrates; Track B reserves necessary-revision, evaluator-private identification, and decision-superiority claims for sealed protocols. The core API now distinguishes an exact minimum policy from a sound cap-limited witness. Deterministic scaling artifacts no longer contain timing values.

One Track A slice was completed on five CPython incremental decoder implementations. A finite-horizon opaque adapter passed complete replay over 90 states and 630 edges. Full adaptive identity required an exact minimum worst-case depth of 3, whereas a declared two-class routing decision required 1. A direct black-box replay matched every candidate path. A predeclared outside-family `cp437` target produced an observation absent from the frozen policy on its first action, yielding `outside_model`. This is external instrument evidence, not ontology invention or necessary revision.

## 1. Solved slice

> Given a frozen finite candidate set and intervention interface, determine whether a predeclared candidate, target-class, or decision distinction can be guaranteed identifiable; synthesize and verify a policy when it can; otherwise distinguish exact impossibility from cap-limited uncertainty.

The target can be complete identity, a coarser representation class, a safety class, or a common-optimal decision region.

## 2. Exact adaptive characterization

The uncertain world is a candidate plus its current internal state. Actions generate outputs and update each surviving candidate state, inducing a finite reachable belief graph.

Target-pure beliefs have rank 0. A belief enters rank \(k+1\) when some action sends every possible observation successor into rank at most \(k\). With complete enumeration, the initial rank is the exact minimum worst-case policy depth. The complement is a closed losing set and supplies a finite impossibility certificate.

With incomplete capped enumeration, a rank-decreasing tree can still be a sound feasibility witness. Version 0.2 therefore returns `witness` and treats its depth only as an upper bound. It never infers impossibility from a cap.

## 3. Why target and decision identification matter

Complete ontology identity can be unnecessarily expensive. In the internal three-candidate pilot, two candidates differ behaviorally but recommend the same repair. Identity needs two probes while the repair class needs one.

The opened codec audit supplied a stronger finite-state example: full identity had an exact adaptive depth of 3 and no finite preset solution, while the decision class had both adaptive and preset depth 1.

## 4. Why task loss matters

Information-gathering actions may affect the system being diagnosed. OIA-1 can preserve candidate-wise net outcomes rather than collapsing every probe to one scalar cost. Its exact Pareto-frontier routine allows Bayesian and maximin policies to differ and returns `unknown` if a declared frontier cap prevents completeness.

The codec audit used only a simple model-independent cost and an instrument-level routing utility. No operational value claim is made from that utility.

## 5. Validation

The current package passes:

| Check | Count |
|---|---:|
| Deterministic tests | 22 |
| Pairwise randomized checks | 1,027 |
| Adaptive randomized checks | 200 |
| Preset randomized checks | 200 |
| Bayesian task-loss randomized checks | 250 |
| Robust task-loss randomized checks | 250 |
| **Total randomized differential checks** | **1,927** |
| External adapter states / edges | **90 / 630** |

The external audit exposed a real partition-convergence bug after the generated suite had passed. The failed numbered audit and fix are retained rather than erased.

## 6. Two-track implication

Track A is useful precisely because it can reveal adapter, scaling, and policy defects in opened environments without requiring every development iteration to satisfy sealed-confirmatory standards. Its claims remain narrow.

Track B is still required to show that:

1. a base representation cannot express a held-out behavior;
2. a newly invented structural construct is necessary rather than merely convenient;
3. evaluator-private interventions identify it;
4. it transfers to untouched reserves; and
5. it improves a predeclared external decision beyond strong alternatives.

## 7. Current conclusion

OIA-1 now has a validated exact finite core, unambiguous cap semantics, reproducible structural evidence, and one end-to-end opened external instrument result. It can determine whether supplied distinctions are behaviorally testable and decision-relevant through a bounded interface, and it can detect when a prospective observation falls outside every supplied candidate.

It still does not form ontologies autonomously. Its role is to make later ontology-discovery claims harder to fake and easier to falsify.
