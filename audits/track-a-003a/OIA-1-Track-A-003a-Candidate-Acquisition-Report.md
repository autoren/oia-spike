# OIA-1 Track A 003a candidate-acquisition feasibility audit

**Audit:** `OIA-1-TRACK-A-003a`  
**Date:** 2026-08-21  
**Gate verdict:** **`resource_authorization_required`**  
**Admitted candidates:** **0**  
**Candidate behavior inspected:** **no**  
**OIA separability consulted:** **no**

## Scope and baseline integrity

This was the opened acquisition gate only. The independently accepted OIA-1 v0.2.1 baseline was hashed but not modified, extracted for development, or repackaged:

```text
2653020afcbf636def260da1517c9e3ba41c2ba1175fc210d4847b303febc33b  OIA-1-v0.2.1-Reproducibility-Maintenance-Package.zip
```

No `cp437` execution, new ARC action, OIA-selected intervention, private/sealed ARC environment, paid model/API call, credential request, or Track B procedure occurred.

The candidate source, opened prefix, admission rule, finite deduplication boundary, and stop rule were frozen before downloading candidate bytes, inspecting candidate behavior, or consulting OIA separability:

```text
47c18e32ea64a19d45842fd13d2a80ab59161992aaef7c13cf501459de75ea59  OIA-1-Track-A-003a-Frozen-Protocol.json
```

## Pinned public authorities

| Component | Exact authority | Version/dependencies | License |
|---|---|---|---|
| ARC toolkit | `arcprize/ARC-AGI@f12822c4d550121c35a275008d964afbbed47d2f` | `arc-agi 0.9.9`, Python `>=3.12`; declared runtime dependencies recorded in source pins | MIT |
| ARC engine | `arcprize/ARCEngine@b495c6acaf253c9681cd7b75c4299d352e9ce6f8` | `arcengine 0.9.3`, Python `>=3.12`; `numpy>=1.24.0`, `pydantic>=2.10.6` | MIT |
| Selected learner | `astroseger/arc-3-agents-baseline1@ef104f198adf2ad2a3506638dc21d0249eb8308c` | `ewma_sv_v1.6`; Codex CLI `0.144.1`; server `arc-agi==0.9.9`; Docker/apt image digests are not locked | MIT |
| Released run record | Zenodo `10.5281/zenodo.21412274` | selected file below | CC BY 4.0 record license |

The selected public environment is `ls20`. The source repository reports complete `ls20` runs for GPT-5.6-sol at both max and xhigh effort: 461 and 465 environment actions respectively. Those rows are evidence that the runs exist, not executable candidates.

## Released learner and candidate-frontier finding

Rodionov's implementation naturally creates a potential candidate frontier. Before each learner iteration, `run_git_snapshot` performs `git add -A`, commits the full workspace, and force-tags it as `iteration_N`. The fixed-interface treatment supplies executable dynamics, initial-state reconstruction/rendering, planning, exact settled-frame replay tools, and session files that retain intermediate animation frames.

Therefore the source architecture passes a limited feasibility question: **multiple fixed executable checkpoints can naturally exist**. It does not establish that the public archive retained the Git objects/tags, that each checkpoint is dependency-complete, or that two checkpoints can be initialized from one byte-identical prefix.

The frozen opened prefix is `ls20_P0_reset_observation`: the complete released reset packet before the first environment action. It contains zero actions. Every admitted candidate would have to share the same full game version, P0 packet, available-action metadata, status, level, and settled frame. This choice permits cross-run initialization without issuing or selecting a new real ARC action.

## Frozen admission and finite behavior rule

Candidate attempts would be drawn from the final max/xhigh world models, then exact `iteration_N` commits or immutable snapshots, retaining at most eight behaviorally unique candidates. Admission requires:

- complete released bytes, dependencies, source/run provenance, hashes, and licenses;
- exact P0 initial-state reconstruction and settled-frame/status replay;
- fresh-process deterministic execution under `PYTHONHASHSEED=0,1,5,10`, twice per word;
- process restart or local reset from P0 with no ARC, LLM, service, credential, web, or hidden conversation state;
- candidate-independent actions from P0 metadata;
- run-level game-source/web leakage inspection;
- explicit audit of state initialization and all file reads; and
- finite behavioral deduplication before any OIA separator analysis.

For simple actions, deduplication enumerates every word of lengths one through three. If ACTION6 is available, its official finite coordinate domain is all 4,096 `(x,y)` values and 003a uses every one-step click plus each one-step simple action. No candidate-selected click targets are allowed. This boundary is only a bounded divergence screen; absence of divergence would not be called global equivalence or impossibility.

ARC can return ordered multi-frame observations. The source session tooling preserves intermediate frames, but its executable verifier checks the final settled frame and status. Accordingly, the protocol preserves all released frames as evidence while limiting candidate replay claims to settled-state semantics. It makes no animation fidelity claim.

## Acquisition attempts and blockers

### Rodionov primary release

The exact selected archive is:

```text
Zenodo record:  21412274
File:           article2_main_runs_additional.tar.gz
Size:           797,835,543 bytes (760.875 MiB; 0.743 GiB)
Upstream MD5:   4dd279f099609392c30cffa468801316
Record license: CC-BY-4.0
```

GitHub exposes the learner, empty initial model stubs, checkpoint mechanism, verifier, and aggregate run tables. It does not expose the generated `ls20` candidate bytes, P0, run-tree inventory, Git objects, dependency closure, or full ordered traces. The archive metadata does not provide an internal tar listing.

Downloading and read-only extracting this 797.8 MB compressed object is the smallest remaining public route found. It is a material transfer and likely requires roughly 2–5 GiB of temporary disk. Under the prompt's explicit scarce-resource stop, it was **not downloaded**. No monetary cost, API key, model call, or real ARC action is required for that next operation.

### Other public options exhausted

- Rodionov's paper01 Dropbox full-run links were inspected at the source/metadata level, but no candidate bytes were acquired; the smaller, checksummed Zenodo artifact is the cleaner next source.
- OPINE-World was inspected secondarily at commit `e1553f29843a41a3d0b70d8a28357577d8b16849`. Its code and lockfile are pinnable and it publishes an 804 MB run archive, but the pinned repository had no root `LICENSE` or project-license field, no immutable archive checksum was acquired, and no exact intermediate executable frontier was available without another large download. It did not displace the primary source.

Every attempt and rejection/deferment is recorded in `OIA-1-Track-A-003a-Attempt-Provenance-Registry.json`.

## Verdict

**`resource_authorization_required`**

This is not a replay failure, single-model result, or lack-of-divergence result. Zero candidate programs were admitted because the first operation capable of exposing them is the 797,835,543-byte archive download/extraction, and the audit was required to stop before that scarce-resource use.

The exact next requirement is:

1. authorize download of `article2_main_runs_additional.tar.gz`;
2. verify upstream MD5 `4dd279f099609392c30cffa468801316` and compute a local SHA-256;
3. extract read-only and inventory only the two selected `ls20` run trees;
4. test whether final models and retained `iteration_N` checkpoints are dependency-complete;
5. hash P0 and enforce the frozen admission/deduplication protocol locally, without ARC or model/service calls.

If the archive contains no usable snapshots, the next numbered opened audit may legitimately end as `single_model_only`, `state_initialization_blocker`, `replay_failure`, another allowed blocker, or `unknown`. No outcome is presumed here.

## Claim boundary

This 003a result establishes only that the selected public source has a natural checkpoint mechanism and that a specific released archive is the concrete acquisition boundary. It does not establish an admissible candidate frontier, behavioral divergence, global equivalence, OIA separator feasibility, ontology identification, necessary revision, decision superiority, sealed transfer, or any Track B claim.
