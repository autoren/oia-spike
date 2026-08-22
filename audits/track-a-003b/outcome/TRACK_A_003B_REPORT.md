# OIA-1 Track A 003b local candidate-admission report

**Gate verdict:** `candidate_frontier_feasible`

**Admitted bounded behaviors:** 2

**Source records screened:** 13

**Real ARC actions:** 0

**OIA separator runs:** 0

## Result

The acquired release contains a usable opened candidate frontier for the frozen level-1 `ls20` boundary. Two fixed programs—`max/final` and `max/iteration_2`—exactly reconstruct the same released reset observation and make deterministic, behaviorally different predictions over all 84 action words of lengths one through three.

This is progress at the intended research resolution. It establishes that the next OIA integration does not need synthetic placeholder candidates. It does not establish that either model is correct or that their difference matters in the real environment.

## Prospective ordering and isolation

Candidate source, order, P0, actions, finite boundary, deduplication rule, and admission requirements were frozen in Track A 003a and the 003b checkpoint rule before behavior inspection. The exact adapter, three-file bundle boundary, dependencies, runtime image, 13 candidate bundle hashes, and container controls were then merged in `PRE_OUTCOME_RUNTIME.json` before acquired candidate execution.

Execution used image `sha256:644d899fa00c3a9fc16cc05f94ee5d078653891fe55659cd8e51fb1126027051` with:

- network disabled;
- a read-only root filesystem and read-only candidate/P0 mounts;
- all Linux capabilities dropped and `no-new-privileges` enabled;
- unprivileged UID/GID `65532:65532`;
- memory, CPU, PID, timeout, and temporary-filesystem bounds; and
- no released session file, credential, service URL, later observation, scorecard, action history, reasoning log, or planner output in a candidate bundle.

The first post-P0 orchestrator invocation exposed an evidence-envelope bug before entering the provisional candidate loop. The original frozen source was preserved, the negative was recorded, and an envelope-only v2 correction was merged before any action-word prediction. It did not change candidate bytes, order, runner, isolation, actions, traces, seeds, repetitions, or admission rules.

## P0 replay

All 13 records passed isolated reconstruction and rendering of the same released P0:

```text
environment:          ls20-9607627b
P0 text/frame SHA-256: 0fc0241eb2d3c992a2af68643f36e3878f5140fc85aed38410dd66ef5486afc7
metadata SHA-256:      0f1dfbd539066cba7373dcce2004196480db34dc2f8c01477e66e711b0c74347
status:                RUNNING
modeled level:         1
actions:               ACTION1, ACTION2, ACTION3, ACTION4
```

The P0 audit observed only reads of the immutable P0 files, the three candidate modules, and failed read probes for disabled bytecode caches. Candidates emitted no stdout or stderr.

## Provisional behavioral deduplication

Each of the 13 records ran every frozen word once under `PYTHONHASHSEED=0`, from a fresh process and fresh P0. All 1,092 processes returned successful predictions. The records collapsed to two trace signatures:

| Earliest candidate | Trace signature | Records in class |
|---|---|---:|
| `max/final` | `f88878cf224dd90aa938d911b10cf66f921e0af8525f88f19db43f7a7f132f01` | 12 |
| `max/iteration_2` | `c45ef446b324b02835f0f8fab854107f7cef7b879f969da800b9b69ac74719f9` | 1 |

The other final worktree and ten other retained checkpoints are bounded behavioral duplicates of `max/final`; they receive no full determinism claim beyond the successful seed-0 screen actually run.

The first divergence is the one-step word `ACTION2`:

| Candidate | Predicted settled frame SHA-256 | Status |
|---|---|---|
| `max/final` | `5e5b28124c21e10f3ffb686006ed454aef743f399e219ffc25d81f7acdec7002` | `RUNNING` |
| `max/iteration_2` | `0fc0241eb2d3c992a2af68643f36e3878f5140fc85aed38410dd66ef5486afc7` | `RUNNING` |

`max/iteration_2` predicts the unchanged P0 raster; `max/final` predicts a changed raster. This is bounded predictive non-equivalence, not evidence about the real `ACTION2` outcome.

## Full determinism promotion

Only the two provisionally unique representatives were promoted. For each of 84 words, both candidates ran twice in fresh processes under `PYTHONHASHSEED` 0, 1, 5, and 10:

| Candidate | Fresh runs | Nondeterministic words | Result |
|---|---:|---:|---|
| `max/final` | 672 | 0 | admitted |
| `max/iteration_2` | 672 | 0 | admitted |

Every promoted trace was byte-identical across all eight processes for its word and matched its provisional signature. No timeout, prediction error, or forbidden runtime event entered a retained trace.

## Attempt and dependency accounting

The audit used 2,449 fresh candidate processes: 13 P0 replays, 1,092 provisional word processes, and 1,344 full-matrix processes. Those processes evaluated 6,612 predicted transitions and executed zero real ARC actions, network/service calls, credentials, model/API calls, or OIA separator runs.

Candidate source provenance remains the MIT-licensed learner commit and the CC BY 4.0 released record pinned in 003a/003b. The runtime is Python 3.12.11 with exact arm64 wheel hashes for NumPy 2.2.6 and SciPy 1.15.3. Their installed distributions carry BSD-family project notices and bundled dependency notices; the wheel bytes are pinned in `runtime/track-a-003b/requirements-aarch64.txt`. The runtime image is an execution artifact and is not redistributed in this repository.

The complete raw P0, provisional, and full JSON evidence remains under ignored `local-work/`; `ADMISSION_SUMMARY.json` records its exact SHA-256 values and complete candidate accounting.

## Claim boundary and next direction

Supported: at least two fixed released programs exactly replay one opened P0 and produce deterministic, behaviorally different predictions inside the frozen 84-word level-1 boundary.

Not supported: global non-equivalence, candidate correctness, a real-environment outcome, animation fidelity, an OIA-selected separator, necessary ontology revision, planning value, decision superiority, sealed transfer, or any Track B conclusion.

The next scientific step must be a separately frozen gate. Reusing these fully inspected traces cannot support a prospective OIA-discovery claim. A useful next gate can either (a) perform a clearly labeled retrospective adapter/instrument integration on this frontier, or (b) pre-register a new opened candidate/environment slice and let OIA select a separator before its model or real outcome is inspected. No such gate is authorized or run here.
