# Tycho local-Qwen evaluator package R0

This integration is a credential-free packaging qualification. It follows the
opened local-Qwen/Tycho action-compatibility result without treating that result
as evidence of correct play.

The official `llama.cpp` release does not publish a Linux/CUDA tarball. It does
publish an immutable Linux/amd64 CUDA OCI image. R0 therefore tests whether the
server and its user-space libraries can be extracted into an ordinary read-only
directory and launched in a clean Linux process without an inner Docker daemon.

One exploratory extraction occurred before the freeze. It correctly exposed an
incomplete bundle: `libgomp.so.1` was inherited from the OCI base image. A second
exploratory check showed that explicitly including all non-glibc dependencies
leaves only `libcuda.so.1`, which must come from the evaluator host driver. These
observations select the exact repeated procedure; they are not qualification
evidence.

[`PACKAGE_PROTOCOL.json`](PACKAGE_PROTOCOL.json) authorizes one post-freeze
bundle build and one clean-container portability test. It authorizes no model
copy, model load, inference, GPU execution, ARC start/action, Kaggle access,
upload, Phase A run, submission, hidden game, or OIA run.

Run the static freeze verifier with:

```bash
python scripts/verify_tycho_kaggle_package.py
```

After the protocol commit, the exact local build command is:

```bash
python scripts/build_tycho_kaggle_runtime_bundle.py \
  --execute \
  --output local-work/tycho-kaggle-runtime-b10236
```

The output is deliberately untracked. The compact relative file manifest and
result may be committed after review.

Even a runtime-bundle pass cannot make the evaluator package ready. Tycho's
`run_python` currently relies on Docker/Finch for the isolation that prevents
model-authored Python from reading unrelated evaluator or attached-input state.
Tycho's `host` mode is not an acceptable substitute. R0 must therefore fail
closed on full adapter/package readiness until a real Docker-free isolated
runner and target-GPU load/throughput test exist.

R0 is now complete. The exact post-freeze bundle contains 38 files and 15
symlinks (772,679,288 regular-file bytes). Its clean, network-disabled,
read-only Ubuntu smoke reports the pinned `llama-server` version and resolves
all bundled CUDA user-space libraries; only host-driver `libcuda.so.1` remains
external. See [`PACKAGE_REPORT.md`](PACKAGE_REPORT.md) and
[`PACKAGE_RESULT.json`](PACKAGE_RESULT.json). The verdict remains explicitly
blocked on the Docker-free isolated Python runner, `MyAgent` integration,
target-GPU model load, and throughput.
