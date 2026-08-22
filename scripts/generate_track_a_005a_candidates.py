#!/usr/bin/env python3
"""Generate opaque fresh P0-only candidates with a frozen local MLX model."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005a"
P0_ROOT = AUDIT_ROOT / "p0"
PROVENANCE_PATH = AUDIT_ROOT / "GENERATION_RUNTIME_PROVENANCE.json"
PROMPT_PATH = AUDIT_ROOT / "GENERATION_PROMPT.template.txt"
STANCES_PATH = AUDIT_ROOT / "HYPOTHESIS_STANCES.frozen.json"

EXPECTED_MODEL_REVISION = "3e6447f082e89cc7f0bc6e5441afd38dfce760ff"
EXPECTED_P0_HASHES = {
    "initial_frame.png": "a4866d89296b2191b5f7e056bc61715ff0c340394392bcbb15ceb95c8dd91953",
    "initial_frame.txt": "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6",
    "initial_metadata.json": "3d9543812b624974d09b72111b55c0f99802220ed919ce79aa21b4d5e39a8281",
}
EXPECTED_ACTIONS = ("ACTION6", "ACTION7")
MAX_TOKENS = 1800
BEGIN_MARKER = "<BEGIN_CANDIDATE_PY>"
END_MARKER = "<END_CANDIDATE_PY>"
ALLOWED_IMPORTS = {"copy", "math", "numpy", "typing"}
REQUIRED_FUNCTIONS = {"initial_state", "step", "render"}
REQUIRED_CONSTANTS = {"RUNNING", "LEVEL_COMPLETED", "GAME_OVER"}
FORBIDDEN_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "print",
    "setattr",
    "vars",
}
FORBIDDEN_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.Global,
    ast.Lambda,
    ast.Nonlocal,
    ast.Yield,
    ast.YieldFrom,
)


class CandidateFormatError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_p0() -> tuple[str, tuple[str, ...]]:
    for name, digest in EXPECTED_P0_HASHES.items():
        if sha256_file(P0_ROOT / name) != digest:
            raise ValueError(f"P0 hash changed: {name}")
    metadata = json.loads((P0_ROOT / "initial_metadata.json").read_text(encoding="utf-8"))
    actions = tuple(f"ACTION{value}" for value in metadata["available_actions"])
    if actions != EXPECTED_ACTIONS:
        raise ValueError("P0 action alphabet changed")
    frame = (P0_ROOT / "initial_frame.txt").read_text(encoding="utf-8").rstrip("\n")
    return frame, actions


def verify_model(snapshot: Path, provenance: Mapping[str, object]) -> None:
    if snapshot.name != EXPECTED_MODEL_REVISION:
        raise ValueError("model revision changed")
    model = provenance["model"]
    if model["revision"] != EXPECTED_MODEL_REVISION:
        raise ValueError("model provenance revision changed")
    for record in model["files"]:
        path = snapshot / record["path"]
        if path.stat().st_size != record["size_bytes"] or sha256_file(path) != record["sha256"]:
            raise ValueError(f"model file mismatch: {record['path']}")


def render_prompt(
    template: str,
    stance: Mapping[str, object],
    frame: str,
    actions: tuple[str, ...],
) -> str:
    values = {
        "{{STANCE_ID}}": str(stance["stance_id"]),
        "{{STANCE_INSTRUCTION}}": str(stance["instruction"]),
        "{{CANDIDATE_ID}}": str(stance["candidate_id"]),
        "{{ACTION_NAMES}}": json.dumps(list(actions), separators=(",", ":")),
        "{{P0_FRAME}}": frame,
    }
    result = template
    for key, value in values.items():
        if result.count(key) < 1:
            raise ValueError(f"prompt placeholder missing: {key}")
        result = result.replace(key, value)
    if re.search(r"\{\{[A-Z_]+\}\}", result):
        raise ValueError("unresolved prompt placeholder")
    return result


def extract_code(response: str) -> str:
    if response.count(BEGIN_MARKER) != 1 or response.count(END_MARKER) != 1:
        raise CandidateFormatError("delimiter_count")
    before, remainder = response.split(BEGIN_MARKER, 1)
    code, after = remainder.split(END_MARKER, 1)
    if before.strip() or after.strip():
        raise CandidateFormatError("text_outside_delimiters")
    code = code.strip() + "\n"
    if not code or len(code.encode("utf-8")) > 40_000:
        raise CandidateFormatError("code_size")
    return code


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def validate_code(code: str) -> dict[str, object]:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise CandidateFormatError("syntax_error") from exc
    functions: set[str] = set()
    constants: set[str] = set()
    imports: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef):
            functions.add(statement.name)
        elif isinstance(statement, (ast.Import, ast.ImportFrom)):
            pass
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    constants.add(target.id)
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
            pass
        else:
            raise CandidateFormatError(f"forbidden_top_level:{type(statement).__name__}")
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise CandidateFormatError(f"forbidden_node:{type(node).__name__}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                imports.add(root)
                if root not in ALLOWED_IMPORTS:
                    raise CandidateFormatError(f"forbidden_import:{root}")
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            imports.add(root)
            if root not in ALLOWED_IMPORTS:
                raise CandidateFormatError(f"forbidden_import:{root}")
        if isinstance(node, ast.Call) and call_name(node) in FORBIDDEN_CALLS:
            raise CandidateFormatError(f"forbidden_call:{call_name(node)}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise CandidateFormatError("dunder_attribute")
    missing_functions = REQUIRED_FUNCTIONS - functions
    missing_constants = REQUIRED_CONSTANTS - constants
    if missing_functions:
        raise CandidateFormatError(f"missing_functions:{sorted(missing_functions)}")
    if missing_constants:
        raise CandidateFormatError(f"missing_constants:{sorted(missing_constants)}")
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "functions": sorted(functions),
        "imports": sorted(imports),
        "result": "pass",
    }


def deterministic_zip(path: Path, files: Mapping[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100444 << 16
            archive.writestr(info, files[name])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if os.environ.get("HF_HUB_OFFLINE") != "1" or os.environ.get("TRANSFORMERS_OFFLINE") != "1":
        raise RuntimeError("offline model environment is required")
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise FileExistsError("candidate generation output already exists")
    output_root.mkdir(parents=True)
    raw_root = output_root / "raw-responses"
    candidate_root = output_root / "candidates"
    raw_root.mkdir()
    candidate_root.mkdir()

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    verify_model(args.snapshot.resolve(), provenance)
    frame, actions = verify_p0()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    stances = json.loads(STANCES_PATH.read_text(encoding="utf-8"))["stances"]
    if len(stances) != 8:
        raise ValueError("frozen stance count changed")

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(str(args.snapshot.resolve()))
    sampler = make_sampler(temp=0.0)
    records: list[dict[str, object]] = []
    package_files: dict[str, bytes] = {}

    for stance in stances:
        candidate_id = str(stance["candidate_id"])
        user_prompt = render_prompt(template, stance, frame, actions)
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate one executable uncertainty hypothesis. Follow the "
                    "requested delimiters and source contract exactly."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        response = generate(
            model,
            tokenizer,
            rendered,
            max_tokens=MAX_TOKENS,
            sampler=sampler,
            verbose=False,
        )
        response_bytes = response.encode("utf-8")
        output_token_count = len(
            tokenizer.encode(response, add_special_tokens=False)
        )
        raw_path = raw_root / f"{candidate_id}.txt"
        raw_path.write_bytes(response_bytes)
        record: dict[str, object] = {
            "candidate_id": candidate_id,
            "stance_id": stance["stance_id"],
            "prompt_sha256": sha256_bytes(rendered.encode("utf-8")),
            "raw_response_sha256": sha256_bytes(response_bytes),
            "raw_response_bytes": len(response_bytes),
            "output_token_count": output_token_count,
            "generation": {
                "decode": "greedy",
                "max_tokens": MAX_TOKENS,
                "repairs": 0,
                "temperature": 0.0,
            },
        }
        try:
            code = extract_code(response)
            structural = validate_code(code)
        except CandidateFormatError as exc:
            record.update({"status": "rejected_structural", "reason": str(exc)})
        else:
            code_bytes = code.encode("utf-8")
            code_path = candidate_root / candidate_id / "candidate.py"
            code_path.parent.mkdir()
            code_path.write_bytes(code_bytes)
            record.update(
                {
                    "status": "structurally_accepted_not_executed",
                    "candidate_sha256": sha256_bytes(code_bytes),
                    "candidate_size_bytes": len(code_bytes),
                    "structural_validation": structural,
                }
            )
            package_files[f"candidates/{candidate_id}/candidate.py"] = code_bytes
        records.append(record)

    accepted = [row for row in records if row["status"] == "structurally_accepted_not_executed"]
    package_manifest = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "model_revision": EXPECTED_MODEL_REVISION,
        "model_provenance_sha256": sha256_file(PROVENANCE_PATH),
        "p0_sha256": EXPECTED_P0_HASHES,
        "candidate_count": len(accepted),
        "candidates": [
            {
                key: row[key]
                for key in (
                    "candidate_id",
                    "stance_id",
                    "candidate_sha256",
                    "candidate_size_bytes",
                    "prompt_sha256",
                    "raw_response_sha256",
                )
            }
            for row in accepted
        ],
    }
    package_manifest_bytes = json.dumps(
        package_manifest, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    package_files["CANDIDATE_MANIFEST.json"] = package_manifest_bytes
    package_path = output_root / "CANDIDATE_PACKAGE.zip"
    deterministic_zip(package_path, package_files)

    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005a",
        "status": (
            "fresh_candidate_generation_feasible"
            if len(accepted) >= 2
            else "fresh_candidate_generation_blocked"
        ),
        "model": {
            "repository": provenance["model"]["repository"],
            "revision": EXPECTED_MODEL_REVISION,
            "provenance_sha256": sha256_file(PROVENANCE_PATH),
        },
        "prompt_template_sha256": sha256_file(PROMPT_PATH),
        "stances_sha256": sha256_file(STANCES_PATH),
        "candidate_records": records,
        "accounting": {
            "requested_candidates": len(stances),
            "local_model_inferences": len(stances),
            "output_tokens_recorded": sum(
                int(row["output_token_count"]) for row in records
            ),
            "structurally_accepted_candidates": len(accepted),
            "structurally_rejected_candidates": len(records) - len(accepted),
            "repair_inferences": 0,
            "candidate_processes": 0,
            "candidate_behavior_steps": 0,
            "hosted_or_api_model_calls": 0,
            "network_or_service_calls": 0,
            "oia_processes": 0,
            "real_arc_actions": 0,
        },
        "package": {
            "path": "candidate-generation/CANDIDATE_PACKAGE.zip",
            "sha256": sha256_file(package_path),
            "size_bytes": package_path.stat().st_size,
            "manifest_sha256": sha256_bytes(package_manifest_bytes),
        },
        "claim_boundary": (
            "Fresh local P0-only candidate generation and static structural validation "
            "only; no generated candidate was imported or behaviorally executed."
        ),
    }
    result_path = output_root / "GENERATION_RESULT.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "accepted": len(accepted),
                "audit_id": result["audit_id"],
                "package_sha256": result["package"]["sha256"],
                "rejected": len(records) - len(accepted),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
