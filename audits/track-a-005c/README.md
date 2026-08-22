# Track A 005c: missing-import maintenance

Track A 005b stopped before calibration because every generated program used
`copy.deepcopy` without importing the permitted `copy` module. This successor
freezes one deterministic, semantics-preserving implementation normalization:
prepend `import copy` only when every unbound `copy` use is exactly
`copy.deepcopy` and no `copy` binding already exists.

No model call or broader source repair is allowed. Parent and normalized hashes
are retained. The normalized package must be merged before candidate execution,
after which the exact P0/P1 calibration and all post-P1 behavior/OIA rules from
the merged 005b freeze are reused without relaxation. Step 2 remains closed.
