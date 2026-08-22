# Tycho Docker-free Sandlock gate R1 result

**Verdict:** `sandlock_adapter_locally_qualified_target_and_throughput_unqualified`

The Docker-free isolation mechanism and the narrow Tycho adapter both passed on
the exact local Linux qualification host. Sandlock v0.8.6 reported Landlock ABI
v8 against its ABI-v6 minimum. The exact patch applied to Tycho commit
`f68912a764372ead0a610db2e1c011d41ce5197e`, and its sandbox unit suite passed
14/14 tests.

The live patched adapter allowed workspace read/write and a deterministic grid
rotation. It denied a sibling sentinel, `/etc/passwd`, `/Users`, an outside
write, TCP, UDP, and `/usr/bin/id` child-process creation. Both network endpoints
were reachable by the unsandboxed control. Sandlock's one-second timeout was
mapped back to Tycho as `SandboxResult(returncode=-1, timed_out=True)`, and a
separate 64 MiB memory probe terminated nonzero.

The system Python 3.14 test launcher initially lacked `pytest`, so it collected
and ran zero tests. That launcher miss is disclosed in the result. The single
actual isolated Python 3.12 suite then collected and passed all 14 tests; no
failed test was retried or tuned around.

## What this clears

The result removes the prior assertion that Tycho necessarily needs Docker or
Finch for safe `run_python`. A pinned, unprivileged Sandlock binary can enforce
the needed process boundary on a sufficiently capable Linux kernel, and the
patch preserves Tycho's existing container and host paths while requiring
Sandlock to be selected explicitly.

## What it does not clear

This is not evidence that the competition evaluator exposes Landlock ABI v6,
permits Sandlock's seccomp supervisor, or runs the pinned x86_64 asset. It says
nothing about the Tycho-to-MyAgent lifecycle adapter, target-GPU model loading,
nine-hour throughput, ARC performance, OIA discovery or transfer, or hidden
evaluation. Host Python remains an explicitly forbidden substitute.

The next useful gate is a credential-free, model-free target-kernel preflight:
carry the 11.4 MB pinned x86_64 Sandlock release asset and this exact probe into
one internet-disabled evaluator notebook, then run only the bounded isolation
checks. A target blocker is an acceptable result.
