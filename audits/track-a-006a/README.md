# Track A 006a: controlled open-world diagnostic

OIA's exact adaptive identity policy is synthesized under a closed candidate
frontier. Its `outside_model` response is sound when a prospective observation
has no policy branch, but the instrument does not claim that every
outside-frontier system must reveal a novel observation along that policy.

This slice measures that limitation in a deterministic controlled simulation.
Each accepted case contains four behaviorally distinct three-state candidates
whose first observation is deliberately uninformative. Unchanged OIA-1 v0.2.1
synthesizes an exact minimum-worst-case identity policy. Four in-family targets
and one independently generated, globally behaviorally distinct outside target
are then executed without exposing target transitions to any policy.

The OIA policy is compared descriptively with an equal-horizon greedy one-step
partition policy and 32 deterministically seeded uniform-random policies per
target. Primary outcomes are outside-target detection and false candidate
identification; in-family identification is a required soundness check. This is
not a superiority test and includes no statistical sampling claim.

## Why this is not duplicate implementation validation

The baseline randomized suites compare synthesis results with independent
exhaustive oracles. They establish algorithmic correctness. Track A 006a instead
executes already-synthesized policies against independently generated hidden
targets, including targets known to be outside the supplied model frontier.

## Prefreeze fixture

A disjoint three-case fixture seed validated the complete generation,
execution, aggregation, and deterministic-evidence path. All 12 in-family OIA
runs were correct. All three fixture outside targets aliased a candidate along
the OIA policy and were falsely identified; uniform random exploration detected
two of twelve outside trials. These fixture counts motivated no protocol change
and are not treated as benchmark evidence.

The benchmark namespace contains 64 cases and has not been generated at this
freeze. Once this freeze is merged, the deterministic benchmark may be run once
in a successor outcome commit. Its strongest possible claim is a controlled
Track A characterization of open-world detection coverage for a closed-world
identity policy. It is not external validation, ontology learning, necessary
revision, sealed transfer, or decision superiority.

