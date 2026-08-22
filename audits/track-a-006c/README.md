# Track A 006c: resettable sequential fusion

Track A 006b improved aggregate outside detection with two sentinels, but its
changed intervention path lost seven detections made by the closed identity
policy. This slice tests a composition that preserves closed-policy novelty by
construction: run the closed policy first, and only after a candidate result
reset the target and run the reject-aware policy as confirmation.

The final rule identifies a base candidate only when both runs identify the
same candidate. An unsupported output in either run, an explicit sentinel-leaf
reject, or disagreement between candidate identities produces an outside
decision. A closed-policy novelty result stops immediately and therefore cannot
be lost by the second policy.

This rule was inspected retrospectively on the fully opened 006b traces. It
would have detected 42 of 64 outside targets while retaining 256/256 in-family
identification, compared with 16 and 29 detections for its components. Those
opened counts are method development only and are isolated in
`OPENED_SEQUENTIAL_DEVELOPMENT.json`.

## Prospective execution

The held-out slice reuses the frozen 006b machine-generation and exact-policy
semantics under a new seed. Each of 64 future cases has four base candidates,
two sentinels, and one outside target globally behaviorally distinct from all
six synthesis machines. It records standalone component outcomes and the fixed
sequential fusion on four in-family and one outside target per case.

A reset is a required, explicit capability: it must restore the same target to
its verified initial state before the reject-aware run. Reset markers and counts
are preserved separately and are not counted as intervention steps. If an
external adapter cannot verify reliable reset, the composition is inapplicable;
this synthetic study does not relax that requirement.

A disjoint three-case fixture passed deterministic generation, fusion, reset
accounting, in-family soundness, and byte-stable packaging. It generated no
held-out case. The benchmark may run once only after the freeze is merged.

## Claim boundary

This is a controlled Track A composition diagnostic. It does not establish
external validation, population-level superiority, semantic novelty, learned
ontology formation, necessary revision, sealed transfer, real ARC performance,
or Track B evidence. It neither executes nor authorizes the pending Track A
005e real ARC gate.
