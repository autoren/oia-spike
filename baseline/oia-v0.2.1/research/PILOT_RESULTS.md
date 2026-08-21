# OIA-1 Internal Validation Results

**Core version:** v0.2.0  
**Date:** 2026-08-21  
**Evidence class:** formal construction and implementation validation; external Track A evidence is reported separately

## 1. Implemented finite core

The core includes:

- deterministic complete finite Mealy candidate validation;
- exact behavioral partition refinement;
- shortest pairwise product-graph separators;
- complete reachable-belief enumeration;
- exact minimum-worst-case adaptive target policies;
- verified cap-limited adaptive policy witnesses with non-optimal depth claims;
- closed losing-set impossibility certificates and a separate verifier;
- shortest preset target sequences and exact preset impossibility;
- common-optimal decision identification;
- expected and robust finite-horizon value with scalar action costs;
- expected and robust finite-horizon value with candidate-dependent task loss;
- JSON input/report generation; and
- a command-line entry point.

## 2. Deterministic tests

The v0.2 suite contains 22 passing tests. In addition to the original separator, alias, adaptive/preset, decision-value, task-loss, serialization, and tamper-rejection checks, it now verifies that:

- cap-limited adaptive feasibility is returned as `witness`, not an exact minimum;
- cap-limited search never reports impossibility;
- serialized witness metadata cannot be changed to claim exact optimality; and
- the external codec partition converges after the stable-partition/block-renumbering regression discovered in Track A audit 001.

## 3. Randomized differential validation

All generated checks use seed `20260821` and compare the optimized core with deliberately smaller independent exhaustive oracles.

| Component | Generated systems | Checks | Result |
|---|---:|---:|---|
| Pairwise separation/equivalence | 200 static + 100 dynamic-pair | 1,027 | pass |
| Adaptive minimum depth | 200 static | 200 | pass |
| Preset minimum length | 200 static | 200 | pass |
| Bayesian candidate-dependent task loss | 250 dynamic two-candidate | 250 | pass |
| Robust candidate-dependent task loss | 250 dynamic two-candidate | 250 | pass |
| **Total randomized differential checks** |  | **1,927** | **pass** |

## 4. Hand-built pilot cases

### Decision region versus full identity

Three static candidates require two probes for full identity, but one probe for the shared repair decision. With utility 10 for the correct repair and cost 1 per probe, expected value rises from \(20/3\) to 9 and robust value from 0 to 9.

### Behavioral alias impossibility

Two candidates with identical outputs and transitions form one exact behavioral-equivalence class. Pairwise, adaptive, preset, and label-target identification all correctly report impossibility; the adaptive report carries a closed losing-set certificate.

### Delayed separator

Two candidates require `prime`, then `inspect`; a one-step audit would incorrectly call them indistinguishable. Product-graph breadth-first search returns the exact shortest length 2.

### Candidate-dependent task loss

Two one-step probes both identify the true model. One is uniformly moderate loss; the other is cheap in the likely world and expensive in the rare world. The Bayesian and maximin policies correctly choose different probes.

## 5. Deterministic structural scaling evidence

The checksummed scaling artifact contains no timing values. Its SHA-256 is:

```text
78b73bf5faf5b21f7d57a5c40cabab883d306399583a1b82817eea491554d2b0
```

### Isolate-one family

| Candidates | Adaptive depth | Reachable beliefs | Preset length | Explored partitions |
|---:|---:|---:|---:|---:|
| 4 | 3 | 11 | 3 | 7 |
| 6 | 5 | 37 | 5 | 31 |
| 8 | 7 | 135 | 7 | 127 |
| 10 | 9 | 521 | 9 | 511 |
| 12 | 11 | 2,059 | 11 | 2,047 |

### Delayed pair family

For delay \(d\), the exact shortest separator length is \(d+1\). The structural artifact covers delays 4, 8, 16, 32, 64, and 128.

## 6. Defects found by validation

The research record preserves three relevant implementation defects or inconsistencies:

1. early random validation found non-monotone partition refinement that could merge/split cyclic blocks;
2. v0.1 documentation overstated adaptive cap semantics by failing to distinguish a sound capped witness from a certified minimum; and
3. the first opened external audit exposed stable-partition numeric relabeling that prevented convergence despite no further semantic split.

Each was fixed and given a regression or metadata-verification test.

## 7. Evidence boundary

The internal tests establish agreement and certificate validity for bounded deterministic cases. They do not establish candidate invention, semantic grounding, necessary ontology revision, or external decision value.

The separate opened external instrument result is in `TRACK_A_002_REPORT.md`. It adds adapter fidelity and prospective outside-model evidence while remaining below the Track B claim boundary.
