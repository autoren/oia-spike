# Next opened gate: isolated local candidate admission

The byte/provenance inventory is complete. It establishes that the acquired artifact contains two exact final worktrees and eleven intact `iteration_N` Git checkpoints, with all thirteen candidate records carrying a byte-identical level-1 reset packet. It does **not** admit a candidate or inspect behavior.

The next gate is frozen in [`LOCAL_ADMISSION_PROTOCOL.frozen.json`](LOCAL_ADMISSION_PROTOCOL.frozen.json). It keeps the research progressive: candidates receive a cheap static and P0 screen first, a single-seed 84-word divergence screen second, and the full eight-process seed/repetition check only if they are provisionally unique.

## Why isolation is required

Both released final worktrees are dirty relative to `HEAD`, and both contain later observations plus a session-state file with service and credential fields. Those values are provenance risks, not runtime inputs. The admission harness must therefore copy only the fixed executable interface and canonical P0 into a network-disabled, read-only container. It must not import candidate code on the host or expose the released session state.

## Current evidence

- Git object integrity passes for both run repositories.
- The retained order contains 11 exact commits: max iterations 1–6 and xhigh iterations 1–5, round-robin by iteration after the two final worktrees.
- Every final/checkpoint P0 PNG, text raster, and metadata file is byte-identical.
- Both scorecards identify the same released environment, `ls20-9607627b`.
- P0 exposes only `ACTION1` through `ACTION4`, so the frozen boundary is exactly 84 action words of lengths one through three.
- Static core imports require the standard library plus NumPy; some max candidates additionally require SciPy. No candidate behavior has run.

## Required implementation sequence

1. Build and hash one dependency-complete container image without candidate bytes.
2. Implement a candidate-independent adapter for `initial_state_reconstruction`, `state_renderer`, and `world_model_engine`.
3. Add a bundle builder that reads final files or exact Git blobs, verifies every hash, and excludes `.git`, session state, later observations, logs, scores, and action histories.
4. Run the exact P0 replay in the isolated container.
5. Run seed-0 provisional deduplication in the frozen candidate order.
6. Promote only behaviorally unique candidates to the complete seed/repetition matrix.
7. Preserve attempt accounting, canonical traces, image/runtime hashes, tests, and a final allowed verdict.

No real ARC action, model/API call, credential, hosted service, private or sealed environment, OIA-selected intervention, or Track B procedure is authorized by this gate.
