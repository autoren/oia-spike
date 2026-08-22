# OIA-1 Track A 003b

Track A 003b resolved the 003a resource boundary by acquiring the selected public `ls20` material without executing candidates or ARC.

The first authorized workflow attempt verified the 797,835,543-byte source archive but selected zero files because the published run labels and archive directory aliases differ. That negative is preserved. Agent 02 then froze an alias correction and checkpoint enumeration rule before inspecting checkpoint behavior. Corrected attempt 02 selected 10,683 regular files totaling 28,897,676 bytes.

This repository independently downloaded the exact Actions artifact ZIP, verified its upload and inner-package hashes, rejected unsafe filesystem entries, verified every payload and selected-file checksum, and materialized the payload read-only under ignored `local-work/`.

See [`evidence/agent02-attempt02/`](evidence/agent02-attempt02/) for the compact imported evidence and provenance. The 8.5 MB artifact ZIP, inner package, 36.6 MB extracted evidence tree, and candidate-bearing files are intentionally not committed.

## Local import

With GitHub CLI authentication available:

```bash
mkdir -p local-work/track-a-003b/agent02-attempt02
gh api repos/autoren/ontology-intervention-auditor/actions/artifacts/9465881649/zip \
  > local-work/track-a-003b/agent02-attempt02/artifact-9465881649.zip
python scripts/import_track_a_003b.py \
  local-work/track-a-003b/agent02-attempt02/artifact-9465881649.zip \
  --destination local-work/track-a-003b/agent02-attempt02/imported-payload \
  --report local-work/track-a-003b/agent02-attempt02/IMPORT_VALIDATION.json
```

The importer fails if the destination already exists. A successful import is read-only and makes no candidate, ARC, model/API, credential, service, OIA, or Track B call.

## Current boundary

Acquisition and read-only inventory are complete. [`CHECKPOINT_INVENTORY.json`](CHECKPOINT_INVENTORY.json) records two exact-but-dirty final worktrees, eleven intact retained Git checkpoints, and one byte-identical P0 packet across all thirteen records. Candidate admission and behavior inspection have not run.

The next opened step is the isolated offline admission procedure in [`NEXT_LOCAL_ADMISSION_GATE.md`](NEXT_LOCAL_ADMISSION_GATE.md), governed by [`LOCAL_ADMISSION_PROTOCOL.frozen.json`](LOCAL_ADMISSION_PROTOCOL.frozen.json). It excludes released session credentials and later observations, executes no real ARC action, and preserves the Track A boundary.

The candidate-independent adapter, exact dependency image, isolation settings, and thirteen minimal bundle hashes are prospectively pinned in [`PRE_OUTCOME_RUNTIME.json`](PRE_OUTCOME_RUNTIME.json). Only its synthetic smoke test has executed; acquired-candidate P0 replay remains the next operation.

All thirteen acquired candidates subsequently passed exact isolated P0 replay. The original host orchestrator then stopped before provisional behavior because it read the saved P0 evidence at the wrong envelope level. [`ORCHESTRATOR_ERRATUM.pre-provisional.json`](ORCHESTRATOR_ERRATUM.pre-provisional.json) preserves that negative and pins the envelope-only v2 correction before any action-word trace.

The completed admission result is in [`outcome/TRACK_A_003B_REPORT.md`](outcome/TRACK_A_003B_REPORT.md), with compact machine-readable accounting in [`outcome/ADMISSION_SUMMARY.json`](outcome/ADMISSION_SUMMARY.json). The allowed verdict is `candidate_frontier_feasible`: two candidates passed exact P0 replay, bounded behavioral non-equivalence, and the full seed/repetition matrix. This remains an opened predictive-model result; no real ARC action or OIA separator ran.
