#!/usr/bin/env python3
"""Hash the local Qwen/MLX generation substrate without running inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


MODEL_REPOSITORY = "mlx-community/Qwen3.8-27B-4bit"
MODEL_REVISION = "3e6447f082e89cc7f0bc6e5441afd38dfce760ff"
MODEL_LICENSE = "Apache-2.0"
EXPECTED_MODEL_FILES = (
    "chat_template.jinja",
    "config.json",
    "generation_config.json",
    "model-00001-of-00003.safetensors",
    "model-00002-of-00003.safetensors",
    "model-00003-of-00003.safetensors",
    "model.safetensors.index.json",
    "preprocessor_config.json",
    "processor_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "video_preprocessor_config.json",
    "vocab.json",
)
EXPECTED_VERSIONS = {
    "mlx": "0.32.1",
    "mlx-lm": "0.31.3",
    "numpy": "2.5.2",
    "safetensors": "0.8.0",
    "tokenizers": "0.22.2",
    "transformers": "5.15.1",
}


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def runtime_record(python: Path) -> dict[str, object]:
    program = """
import json, platform
from importlib.metadata import version
import mlx.core as mx
names = ['mlx','mlx-lm','numpy','safetensors','tokenizers','transformers']
print(json.dumps({
    'python': platform.python_version(),
    'platform': platform.platform(),
    'packages': {name: version(name) for name in names},
    'metal_available': mx.metal.is_available(),
}, sort_keys=True))
"""
    completed = subprocess.run(
        (str(python), "-c", program),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.stderr:
        raise RuntimeError("runtime inventory emitted stderr")
    result = json.loads(completed.stdout)
    if result["packages"] != EXPECTED_VERSIONS:
        raise ValueError("generation runtime versions changed")
    if result["metal_available"] is not True:
        raise ValueError("MLX Metal backend is unavailable")
    return result


def model_record(snapshot: Path) -> dict[str, object]:
    if snapshot.name != MODEL_REVISION:
        raise ValueError("model snapshot revision changed")
    observed_names = tuple(sorted(path.name for path in snapshot.iterdir()))
    if observed_names != EXPECTED_MODEL_FILES:
        raise ValueError(f"model snapshot file set changed: {observed_names}")
    records: list[dict[str, object]] = []
    for name in EXPECTED_MODEL_FILES:
        path = snapshot / name
        if not path.is_file():
            raise ValueError(f"model snapshot entry is not a file: {name}")
        records.append(
            {
                "path": name,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    config = json.loads((snapshot / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "qwen3_5":
        raise ValueError("unexpected model architecture")
    quantization = config.get("quantization")
    if quantization != {"bits": 4, "group_size": 64, "mode": "affine"}:
        raise ValueError("model quantization changed")
    index = json.loads(
        (snapshot / "model.safetensors.index.json").read_text(encoding="utf-8")
    )
    shard_names = sorted(set(index["weight_map"].values()))
    if shard_names != list(EXPECTED_MODEL_FILES[3:6]):
        raise ValueError("weight index shard set changed")
    return {
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "license": MODEL_LICENSE,
        "architecture": config["model_type"],
        "quantization": quantization,
        "files": records,
        "file_count": len(records),
        "total_size_bytes": sum(record["size_bytes"] for record in records),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite runtime provenance: {output}")
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "status": "local_generation_substrate_inventoried_without_inference",
        "model": model_record(args.snapshot.resolve()),
        "runtime": runtime_record(args.python.absolute()),
        "compatibility_smoke": {
            "performed_before_freeze": True,
            "operation": "mlx_lm.load(local snapshot) only",
            "model_class": "Model",
            "tokenizer_class": "TokenizerWrapper",
            "chat_template_present": True,
            "inference_tokens_generated": 0,
        },
        "access_accounting": {
            "model_files_hashed": len(EXPECTED_MODEL_FILES),
            "model_loads": 1,
            "inference_tokens_generated": 0,
            "candidate_generations": 0,
            "hosted_or_api_model_calls": 0,
            "candidate_processes": 0,
            "oia_processes": 0,
            "real_arc_actions": 0,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "audit_id": result["audit_id"],
                "model_file_count": result["model"]["file_count"],
                "model_revision": result["model"]["revision"],
                "status": result["status"],
                "total_size_bytes": result["model"]["total_size_bytes"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
