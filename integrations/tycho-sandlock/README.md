# Tycho Docker-free Sandlock gate R1

This gate tests one narrow successor to the evaluator-package R0 blocker: a
rootless Linux process sandbox for Tycho's model-authored Python. The protocol
is prospectively frozen in `SANDBOX_PROTOCOL.json`. Pre-freeze exploration is
disclosed there and is not counted as the qualifying result.

The strongest possible pass is deliberately local. It can establish that one
pinned Sandlock binary and policy work in one exact Linux VM and that a patch
preserves the pinned Tycho sandbox interface. It cannot establish that the
competition evaluator exposes a sufficient Landlock ABI, that the model fits
or is fast enough, that an evaluator adapter is correct, or that OIA discovers
anything.
