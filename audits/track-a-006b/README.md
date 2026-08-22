# Track A 006b: reject-aware sentinel diagnostic

Track A 006a showed that an exact closed-frontier identity policy can identify
an outside system as a known candidate whenever the hidden system aliases that
candidate along the selected path. Track A 006b prospectively tests one bounded
response: augment the synthesis frontier with two independently generated
sentinel machines and allow a terminal reject conclusion only after every base
candidate has been eliminated.

The two-sentinel configuration was selected on 16 already-opened 006a cases by
a predeclared parsimony rule: choose the smallest tested sentinel count tied for
the greatest observed outside detection. Counts for 1, 2, 4, and 8 sentinels
were 6, 9, 9, and 9 of 16. This opened development result is recorded in
`OPENED_DEVELOPMENT_SELECTION.json`; it is not outcome evidence.

## Frozen held-out comparison

Each of 64 future held-out cases will contain four globally behaviorally
distinct base machines, two independently generated and globally distinct
sentinels, and one independently generated target globally distinct from all
six synthesis machines. All are complete deterministic three-state Mealy
machines with a shared three-action and three-output alphabet. Initial outputs
are uninformative for every action.

Two policies are synthesized without target access:

- the unchanged OIA-1 v0.2.1 exact identity policy over the four bases;
- an exact minimum-depth policy over bases plus sentinels whose terminal rule is
  either one base with no sentinel remaining (identify) or no base remaining
  (reject).

Both policies run at their native exact depth. The reject-aware policy also runs
at the closed policy's horizon as a secondary fixed-budget diagnostic. Native
in-family identification must be sound. Outside detection is the sum of an
unsupported output (`outside_model`) and a base-eliminated sentinel leaf
(`outside_reject`). A base singleton reached by the outside target is a false
candidate identification.

A disjoint three-case fixture validated deterministic generation, exact policy
verification, execution, and byte-stable evidence. It generated no held-out
benchmark case. The benchmark namespace remains ungenerated at this freeze and
may be executed once only after this freeze is merged.

## Claim boundary

This is a controlled Track A method diagnostic. It can show how the frozen
two-sentinel rule behaves on the specified deterministic held-out corpus. It
cannot establish external validation, learned ontology formation, necessary
revision, semantic novelty, sealed transfer, population inference, comparative
superiority, or Track B evidence. It performs no real ARC intervention and does
not change the pending authorization boundary of Track A 005e.
