# Release Notes — OIA-1 v0.2.1

**Date:** 2026-08-21  
**Class:** narrowly scoped reproducibility and packaging maintenance

## Correction

- Removed hash-order dependence from adaptive equal-depth policy selection.
- Canonically sorts reachable beliefs during rank construction.
- Selects the lexicographically smallest minimum-rank action only after the final rank map is complete.
- Added a cross-process regression over `PYTHONHASHSEED=0,1,2,5,10,42,123`.
- The corrected source produces one report SHA-256 (`10bbdb…f2ce`) and one policy SHA-256 (`612c0572…8799`), matching the historical stored report and policy.

## Historical preservation

- Embedded the exact v0.2.0 release archive unchanged.
- Kept every audit-002 pre-outcome and outcome artifact byte-for-byte unchanged.
- Did not execute `cp437` and did not create a post-outcome refreeze.
- Added a byte-identical snapshot of the original frozen instrument sources.
- Added a separate current-source manifest and a verifier that refuses to substitute current source for historical frozen source.

## Validation

- 23 deterministic tests pass, including the cross-process regression.
- 1,927 randomized differential checks pass.
- Two deterministic scaling runs produce the same structural JSON hash.
- Seven fresh hash-seed processes produce one report and one policy hash.
- Audit-001 and audit-002 nested manifests verify unchanged.
- Historical and current provenance layers verify independently.

## Claim boundary

v0.2.1 adds no external scientific outcome. It repairs canonical serialization and release provenance only. The v0.2.0 Track A finding remains an opened instrument-validation result, and Track B remains unauthorized.

---

# Historical v0.2.0 summary

v0.2.0 introduced the Track A / Track B standard, repaired adaptive cap semantics and deterministic scaling evidence, and completed the opened CPython codec audit with exact identity depth 3, decision depth 1, preset-identity impossibility, five valid direct black-box paths, and prospective `outside_model` detection on `cp437` at step 1.
