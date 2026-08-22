# OIA Spike

This is the standalone local execution workspace for bounded, opened Ontology Intervention Auditor (OIA) research spikes.

It is intentionally separate from [`autoren/ontology-intervention-auditor`](https://github.com/autoren/ontology-intervention-auditor). The Git history through commit `e56f885` was imported from that repository to preserve the Track A 003a and early 003b record. There is no automatic synchronization back to it, and this checkout's `origin` is only [`autoren/oia-spike`](https://github.com/autoren/oia-spike).

## Contents

- [`baseline/oia-v0.2.1/`](baseline/oia-v0.2.1/) is an exact import of the accepted executable OIA-1 v0.2.1 tree from `executable-ontology-lab` commit `3ca35d4`. It includes the core implementation, tests, CPython Track A 002 evidence, maintenance provenance, and Track A/Track B claim boundaries.
- [`audits/track-a-003a/`](audits/track-a-003a/) is the closed candidate-acquisition feasibility audit. Its frozen artifacts and package manifest are unchanged.
- [`audits/track-a-003b/`](audits/track-a-003b/) records the authorized public-archive acquisition and independent local import. The obsolete GitHub-only acquisition workflow has been replaced by a hash-pinned local importer.
- [`audits/track-a-004a/`](audits/track-a-004a/) is the bounded retrospective OIA adapter-integration gate for the two candidates admitted by 003b.
- [`audits/track-a-005a/`](audits/track-a-005a/) is the held-out successor, beginning with a header-only source selection and a fresh P0-only candidate route.
- [`audits/track-a-005b/`](audits/track-a-005b/) records the transient-informed candidate revision and its pre-calibration missing-import blocker.
- [`audits/track-a-005c/`](audits/track-a-005c/) records the frozen one-line import maintenance, exact admission of three behavioral classes, and OIA's prospective `ACTION7` selection.
- [`audits/track-a-005d/`](audits/track-a-005d/) records the public-archive outcome blocker: all five recorded step-2 actions were `ACTION6`, so no `ACTION7` frame was opened or scored.
- [`audits/track-a-005e/`](audits/track-a-005e/) pins the official local `su15` source and freezes an offline outcome protocol. The gate is prepared but remains unexecuted pending explicit authorization for bounded local ARC actions.
- [`audits/track-a-006a/`](audits/track-a-006a/) freezes a controlled prospective diagnostic of closed-frontier identity policies against independently generated outside-frontier targets. It is a synthetic Track A limitation study, not external or Track B evidence.
- [`audits/track-a-006b/`](audits/track-a-006b/) prospectively evaluates a frozen two-sentinel reject-aware policy on a disjoint controlled corpus, with the closed identity policy as a paired baseline. It is a synthetic method diagnostic and does not authorize real ARC execution.
- [`audits/track-a-006c/`](audits/track-a-006c/) prospectively evaluates conservative resettable sequential fusion of the closed and reject-aware policies. It is the final same-family controlled diagnostic, not external or Track B evidence.
- [`docs/context/`](docs/context/) contains curated parent-project decision records needed to interpret the spike. These copies are contextual and are not part of the frozen 003a package.
- [`integrations/tycho/`](integrations/tycho/) contains a source-pinned,
  logging-only patch and credential-free exporter for producing lossless Tycho
  observation streams under the parent project's external trace-bundle
  contract. It does not authorize a model or ARC run.
- [`integrations/discoverphysics/`](integrations/discoverphysics/) contains a
  source-pinned, execution-free context adapter for a possible prospective
  DiscoverPhysics-style study. It rejects the current time-blind submitted-law
  signature, requires `start_time` to reach the artifact and evaluator, binds
  evaluator-held matched pairs by nonce-hardened commitment, and validates
  complete ordered traces. It does not authorize a learner, simulator,
  candidate, or private-world run. The adapter was frozen at `567ea676` and
  its credential-free qualification is recorded in
  [`INTEGRATION_RESULT.json`](integrations/discoverphysics/INTEGRATION_RESULT.json).
- [`integrations/tycho-local-qwen/`](integrations/tycho-local-qwen/) freezes a
  separately bounded local-model engineering qualification: one repeated
  transport call and at most two local-model calls/two actions on one opened
  public ARC-AGI-3 game. The qualification passed for local transport and
  opened-harness compatibility. The sole recorded game action was Tycho's
  default at the original tool cap, not a model-selected action. A separately
  frozen diagnostic then found that equal call/tool ceilings suppressed
  Tycho's built-in final commit-only pass. Holding four analysis tools fixed
  and reserving a fifth commit call produced one explicit, syntactically valid
  model-selected `ACTION1`. Its correctness and progress are unestablished.
  This integration does not authorize a private game, submission,
  executable-world-model generation, or behavioral claim.

## Local baseline validation

The baseline requires Python 3.11 or newer and has no runtime dependencies:

```bash
cd baseline/oia-v0.2.1
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python maintenance/verify_provenance.py
```

Run additional deterministic and randomized checks from the same directory as needed:

```bash
python research/randomized_validation.py
python research/task_loss_validation.py
python research/scaling_probe.py
python research/hash_seed_reproducibility.py
```

## Artifact handling

Downloaded archives, extracted candidate trees, virtual environments, and run outputs belong under `local-work/` or `artifacts/`; both are ignored. Do not commit credentials, private ARC material, service state, or acquired bulk artifacts. Commit only compact manifests, hashes, protocols, and reviewed evidence that the applicable gate authorizes.

The corrected Track A 003b Actions artifact can be verified and materialized read-only with `scripts/import_track_a_003b.py`; see [`audits/track-a-003b/README.md`](audits/track-a-003b/README.md). The importer does not execute candidates or ARC.

Track A 004a compiled the already-known deterministic 003b traces into the
accepted finite OIA interface and passed its retrospective integration gate:
unchanged OIA-1 v0.2.1 certified `ACTION2` as an exact minimum one-step separator.
See [`audits/track-a-004a/README.md`](audits/track-a-004a/README.md).

The 005e and 006a–006c historical freeze manifests included this mutable root
index. Use `python scripts/verify_historical_freeze_continuity.py` to reconstruct
each exact pre-outcome Git snapshot, run its original verifier there, and check
current continuity of every experiment-local manifest entry. The original
manifests and verifiers remain unchanged; see
[`audits/FREEZE_VERIFIER_MAINTENANCE.json`](audits/FREEZE_VERIFIER_MAINTENANCE.json).

## Claim boundary

This workspace remains opened Track A work. It does not authorize paid model
runs, private or sealed evaluation, competition submissions, retroactive
changes to frozen artifacts, or Track B claims. The sole current local-model
exception is the exact opened public-game engineering qualification frozen in
`integrations/tycho-local-qwen/QUALIFICATION_PROTOCOL.json`; it cannot be
generalized to another game, model, call budget, or claim. The accepted
baseline archive remains identified by SHA-256
`2653020afcbf636def260da1517c9e3ba41c2ba1175fc210d4847b303febc33b`.
