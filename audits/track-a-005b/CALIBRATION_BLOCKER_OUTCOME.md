# Track A 005b calibration blocker

The frozen behavior gate returned the allowed verdict
`revision_generation_or_calibration_blocker`.

All eight generated candidates passed the hardened static scan. Each then ran
once in the frozen isolated container. All eight raised `NameError` before an
exact calibration result could be produced, so the gate stopped after eight
candidate processes. No post-P1 action word, OIA process, step-2-or-later
payload, network/service call, credential, real ARC action, or private/sealed
evaluation was used.

Post-blocker source inspection found the same bounded engineering defect in all
eight programs: each calls permitted `copy.deepcopy`, but none binds the name
`copy`. The parser and structural scan accepted the programs because `copy` is
an allowed import root, while the static contract did not require every loaded
global name to resolve. This means the slice did not test whether the proposed
mechanisms reproduce P1; it tested and exposed an insufficient static
executability check.

The result is preserved as-is. The generated source must not be retroactively
edited or the 005b outcome rerun. A separate prospective maintenance slice may
permit only a deterministic missing-`copy` import normalization, preserve both
parent and normalized hashes, and then reuse the unchanged exact calibration,
determinism, behavioral-divergence, and OIA requirements. Any broader repair
requires a new generation slice.
