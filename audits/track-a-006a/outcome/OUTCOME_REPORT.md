# Track A 006a controlled open-world outcome

## Result

The frozen 64-case benchmark completed without a generation, cap, or instrument
blocker. Every accepted candidate frontier had an exact OIA policy of minimum
worst-case depth 3. All 256 in-family OIA executions correctly identified their
candidate, satisfying the predeclared soundness requirement.

On the 64 independently generated targets that were globally behaviorally
distinct from every candidate:

- OIA returned `outside_model` for 17 targets (26.5625%).
- OIA reached a candidate leaf for 47 targets (73.4375%), producing a false
  candidate identification relative to the known controlled ground truth.
- No OIA execution remained unresolved because its policy is guaranteed to
  terminate inside the declared candidate frontier.

The primary result is therefore not an OIA implementation failure. It is a
confirmed limitation of the declared closed-frontier objective: exact candidate
identification does not guarantee exposure of a system outside that frontier.
`outside_model` is a sound reaction to an unsupported observation, not a
completeness guarantee that such an observation will be elicited.

## Descriptive comparators

At the same per-case horizon of three interventions:

| Policy | In-family correct | Outside detected | Outside false ID | Outside unresolved |
|---|---:|---:|---:|---:|
| OIA adaptive | 256/256 | 17/64 | 47/64 | 0/64 |
| Greedy one-step | 182/256 | 9/64 | 37/64 | 18/64 |
| Uniform random | 4,272/8,192 trials | 689/2,048 trials | 890/2,048 trials | 469/2,048 trials |

These are deterministic corpus counts, not population estimates. The uniform
random row contains 32 seeded trials per target and is not an equally sized
paired superiority test. Exploratorily, at least one of the 32 random trials
detected 62 of the 64 outside targets; this was not a predeclared endpoint.

## Generation and reproducibility

- Accepted cases: 64/64.
- Candidate-generation attempts: 65 total; one rejected for candidate
  behavioral equivalence.
- Outside-target attempts: 65 total; one rejected because it was behaviorally
  in-family.
- OIA policy roots: `a0` in 47 cases, `a1` in 14, and `a2` in 3.
- Run records: 10,880.
- Evidence SHA-256: `57b18c6a17e6d879b13e08a8fcad9e942f17672d813eb152e707a50db397efdb`.
- A clean replay regenerated the result JSON and evidence ZIP byte-for-byte.

## Research implication

A future auditor intended for open-world use needs an objective beyond
closed-set identity—such as explicit novelty exposure, frontier-coverage risk,
or a reject option calibrated against alternative behavior families. This
benchmark does not establish which extension is best; it establishes a concrete
failure mode and a deterministic test bed on which such extensions can be
compared.

The claim remains controlled Track A evidence. It is not external validation,
learned ontology formation, necessary revision, semantic grounding, sealed
transfer, statistical population inference, or decision superiority.

