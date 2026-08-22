# Track A 005e: pinned local outcome gate

Track A 005d could not score the frozen `ACTION7` separator because every
available public archive run recorded `ACTION6` at step 2. That is an archive
coverage blocker, not a candidate failure.

This successor removes that blocker without changing the already-merged
candidate set or OIA decision. It records a post-decision acquisition of the
official MIT-licensed `su15-1944f8ab` source and freezes a small, offline local
outcome protocol before the source is imported or any environment is reset.
The source itself remains under ignored `local-work/`; only provenance, hashes,
the protocol, and verification code are committed.

The proposed execution is deliberately small: two independent repetitions for
each of the two already-opened first-action coordinates, each with the exact
sequence `RESET`, `ACTION6(x,y)`, and—only after exact P0/P1 reproduction—
`ACTION7`. No later action is allowed. The runner requires an explicit
`--authorize-local-actions` switch, so the committed freeze and its tests do not
execute the game.

This gate remains closed until real local ARC actions are explicitly authorized.
If it is later run unchanged, its strongest possible positive result is an
opened, maintenance-repaired, prospective one-step outcome relative to the
already-frozen `ACTION7`. It cannot establish untouched-model performance,
sealed transfer, general decision value, autonomous ontology formation, or a
Track B claim.

