# Tycho target-kernel preflight R2a package result

**Verdict:** `offline_target_preflight_bundle_ready_target_execution_pending`

The exact model-free target preflight is packaged and independently verified.
The single frozen build produced a 16,300,425-byte deterministic ZIP with
SHA-256 `21f530d5262858583224f9c0ee1638765da547e521875b8a31bfe446143f731e`.
It contains 76 payload files totaling 25,059,407 bytes; the canonical relative
entry-set hash is
`cac135dace6772d041b539a589baf65377a74893f2494654a0b91794f90bf1b4`.

The bundle contains the exact 12,204,192-byte x86_64 Sandlock executable,
patched Tycho runtime, original source archives and patch, both licenses, a
fail-closed target runner, a standalone offline verifier, and instructions.
Independent verification checked every relative hash and mode, sorted ZIP
paths, fixed timestamps, the 20 MB cap, and ELF machine 62 (`x86-64`).

The runner requires an existing protected input root, performs its own
Sandlock feature check, and stops with a structured blocker if that check
fails. It has no host fallback. Its only live operations are workspace versus
protected-root isolation, reachable localhost TCP/UDP controls, child-process
denial, a one-second timeout, and a 64 MiB memory cap.

No x86_64 binary, Kaggle notebook, credential, model, GPU, ARC environment,
OIA policy, submission, or hidden game executed. The ZIP remains untracked at
`local-work/tycho-target-preflight-r2a/tycho-target-preflight-r2a.zip`; the
compact manifest is tracked as `TARGET_BUNDLE_MANIFEST.json`.

R2b is now the irreducible next step: prospectively freeze and explicitly
authorize one internet-disabled target notebook with this exact ZIP attached.
A target-kernel blocker is an acceptable result and must never trigger host
Python fallback.
