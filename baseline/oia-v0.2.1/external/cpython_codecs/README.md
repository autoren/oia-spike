# CPython Codec Track A Slice

This directory contains the substrate-specific OIA-1 Track A adapter and two numbered diagnostic audits. It is not a general ontology compiler.

## Files and maintenance status

- `codec_adapter.py` — finite-horizon opaque adapter for CPython incremental decoders.
- `validate_adapter.py` — independent fresh-decoder trace replay used during freezing.
- `prepare_audit.py` — original deterministic audit-002 freeze script; refuses to overwrite an audit after a prospective outcome exists.
- `run_opened_audit.py` — byte-identical historical runner. In v0.2.1 its source-provenance check intentionally fails before any write because the corrected `synthesis.py` no longer matches the frozen source hash.
- `execute_prospective_outcome.py` — the one-time opened target runner used for audit 002; it was not executed during v0.2.1 maintenance.
- `audit_001/` — frozen diagnostic attempt closed before outcome after an instrument nontermination defect.
- `audit_002/` — immutable v0.2.0 freeze, pre-outcome selection, black-box replay, prospective outcome, and complete manifests.

The byte-identical v0.2.0 instrument sources named by `audit_002/instrument_source_provenance.json` are retained under `historical/v0.2.0/instrument_sources/`. Corrected current sources are checked separately by `maintenance/CURRENT_SOURCE_SHA256SUMS`. The exact original source is preserved under the historical snapshot. Use `python maintenance/verify_provenance.py` to verify both layers and every unchanged audit-002 artifact against the embedded v0.2.0 archive.

## Audit lineage

### Audit 000

All 256 byte actions plus `finish`, horizon 4. Complete reachable-state/edge replay did not complete within the 120-second engineering cap. No identifiability result was accepted.

### Audit 001

Seven-action diagnostic alphabet. The audit froze successfully, but OIA did not complete before outcome because stable partition blocks were repeatedly renumbered. The target was never executed. The original freeze and closure are both checksummed.

### Audit 002

Same public candidate family and diagnostic boundary, newly frozen after the convergence fix and instrument source-hash freeze. It completed and then executed the one predeclared `cp437` target. Every artifact in this directory remains byte-for-byte unchanged in v0.2.1.

## v0.2.1 maintenance boundary

The original audit-002 instrument sources are preserved under `historical/v0.2.0/instrument_sources/` and authenticated by the unchanged `audit_002/instrument_source_provenance.json`. The corrected active source is authenticated separately by `maintenance/CURRENT_SOURCE_SHA256SUMS`. `maintenance/verify_provenance.py` verifies both layers and requires that only `src/ontology_auditor/synthesis.py` differs within the original frozen instrument-source set.

Current-source deterministic replay uses `research/hash_seed_reproducibility.py`, which consumes only `audit_input.opaque.json` in fresh Python processes. It does not execute any codec implementation or the historical `cp437` target.

### v0.2.1 maintenance

No audit was refrozen and no target was executed. The current core only recomputes the already frozen opaque machine input under multiple fresh hash seeds:

```bash
PYTHONPATH=src python research/hash_seed_reproducibility.py
```

## Revalidate the adapter

```bash
PYTHONPATH=src:external/cpython_codecs python - <<'PY'
import json
from pathlib import Path
from codec_adapter import CANDIDATE_CODECS, HORIZON
from validate_adapter import validate_family
_, result = validate_family(CANDIDATE_CODECS, horizon=HORIZON)
frozen = json.loads(Path(
    "external/cpython_codecs/audit_002/adapter_trace_validation.json"
).read_text())
assert result == frozen
print(result["total_states_checked"], result["total_edges_checked"])
PY
```

## Verify manifests

```bash
python maintenance/verify_provenance.py
(cd external/cpython_codecs/audit_001 && sha256sum -c FREEZE_SHA256SUMS)
(cd external/cpython_codecs/audit_001 && sha256sum -c AUDIT_CLOSURE_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c FREEZE_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c PRE_OUTCOME_SHA256SUMS)
(cd external/cpython_codecs/audit_002 && sha256sum -c FINAL_SHA256SUMS)
```

Audit 002’s prospective outcome is already opened. Any later execution is replication, not a new prospective test.
