# Tycho local-Qwen evaluator package R0 result

**Date:** 2026-08-22  
**Prospective freeze:** `360174465d8d081e4a3f6b409411afee3c9d2780`  
**Verdict:** `runtime_bundle_qualified_adapter_sandbox_and_throughput_unqualified`

## Result

The single authorized post-freeze runtime build and clean-container test
passed. The builder acquired the exact Linux/amd64 `llama.cpp` CUDA 13.3 OCI
manifest, copied `/app` plus every frozen CUDA/non-glibc dependency into an
ordinary directory, and produced a relative file manifest with:

- 38 regular files;
- 15 symlinks;
- 772,679,288 regular-file bytes; and
- entry-set SHA-256
  `a6048e50fc12d4a7ef379b4f03928076ce6a866f4e38eda8a3ec7a8e932eb4e6`.

The portability smoke mounted that directory read-only into the exact clean
Ubuntu 24.04 Linux/amd64 image, disabled the container network, and made the
container root filesystem read-only. The extracted server reported:

```text
version: 10236 (1464c62d8)
built with GNU 14.2.0 for Linux x86_64
```

`libcudart.so.13`, `libcublas.so.13`, and `libcublasLt.so.13` resolved from the
bundle. The only unresolved shared library was `libcuda.so.1`, which correctly
belongs to the evaluator host's NVIDIA driver rather than the attached input.

No model bytes were copied or loaded. No inference, GPU execution, ARC start or
action, credential, external model/API call, Kaggle access, upload, Phase A
run, submission, hidden game, or OIA run occurred.

## Interpretation

The Linux inference runtime no longer needs an inner Docker daemon at
execution time. It can be shipped as normal read-only input files and launched
as an ordinary process, subject to the target host supplying a compatible
NVIDIA driver.

This does **not** make the evaluator package ready. Tycho's model-authored
`run_python` tool still relies on Docker/Finch for filesystem and network
isolation. Setting `TYCHO_SANDBOX_RUNTIME=host` would let generated Python read
unrelated `/kaggle/input` and evaluator state, so R0 rejects that workaround.
The `MyAgent` lifecycle/server manager, target-GPU model load, peak memory, and
110-game throughput are also unqualified.

## Next bounded gate

The next useful engineering slice is a credential-free, model-free feasibility
test for a Docker-free isolated Python runner. The preferred route is a
WebAssembly Python runtime with only the per-game Tycho workspace preopened and
no network authority. It must run representative grid/NumPy analyses while
proving that a sibling sentinel file and network socket are unreachable. A
failure is an acceptable blocker. Ordinary host Python is not an allowed pass.

The complete compact byte/provenance record is
[`RUNTIME_BUNDLE_FILE_MANIFEST.json`](RUNTIME_BUNDLE_FILE_MANIFEST.json), and
the machine-readable result is [`PACKAGE_RESULT.json`](PACKAGE_RESULT.json).
