#!/usr/bin/env python3
"""Apply the one frozen missing-copy-import normalization to Track A 005b."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PARENT_PACKAGE = ROOT / "audits" / "track-a-005b" / "revision-generation" / "CANDIDATE_PACKAGE.zip"
PROTOCOL_PATH = ROOT / "audits" / "track-a-005c" / "MISSING_IMPORT_NORMALIZATION_PROTOCOL.frozen.json"
EXPECTED_PARENT_PACKAGE_SHA256 = "a49a8012b0f7f130feb5c32bfb32825ad4426d7c2203fba6e532165c1fd884d4"
PREFIX = b"import copy\n"

sys.path.insert(0, str(ROOT / "scripts"))
from generate_track_a_005a_candidates import deterministic_zip, validate_code


class NormalizationError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def copy_is_bound(tree: ast.Module) -> bool:
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if (alias.asname or alias.name.split(".", 1)[0]) == "copy":
                    return True
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                if (alias.asname or alias.name) == "copy":
                    return True
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if any(isinstance(target, ast.Name) and target.id == "copy" for target in targets):
                return True
        elif isinstance(statement, (ast.FunctionDef, ast.ClassDef)) and statement.name == "copy":
            return True
    return False


def normalize_source(source: bytes) -> tuple[bytes, dict[str, object]]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NormalizationError("non_utf8_source") from exc
    validate_code(text)
    tree = ast.parse(text, mode="exec")
    if copy_is_bound(tree):
        raise NormalizationError("copy_already_bound")
    parent: dict[ast.AST, ast.AST] = {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }
    loaded_copy = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "copy"
    ]
    if not loaded_copy:
        raise NormalizationError("no_loaded_copy")
    for node in loaded_copy:
        owner = parent.get(node)
        if not (
            isinstance(owner, ast.Attribute)
            and owner.value is node
            and owner.attr == "deepcopy"
        ):
            raise NormalizationError("copy_use_not_exact_deepcopy")
    normalized = PREFIX + source
    validate_code(normalized.decode("utf-8"))
    return normalized, {
        "edit": "prepend_import_copy",
        "inserted_bytes_hex": PREFIX.hex(),
        "copy_deepcopy_use_count": len(loaded_copy),
        "other_source_bytes_changed": 0,
    }


def normalize(output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"normalization output exists: {output_root}")
    if sha256_file(PARENT_PACKAGE) != EXPECTED_PARENT_PACKAGE_SHA256:
        raise ValueError("parent candidate package changed")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    expected = {
        row["candidate_id"]: row["sha256"] for row in protocol["parent"]["candidate_sources"]
    }
    package_files: dict[str, bytes] = {}
    records = []
    with zipfile.ZipFile(PARENT_PACKAGE) as archive:
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("parent package has duplicate paths")
        if any(
            PurePosixPath(info.filename).is_absolute()
            or ".." in PurePosixPath(info.filename).parts
            for info in infos
        ):
            raise ValueError("parent package has unsafe paths")
        parent_manifest = json.loads(archive.read("CANDIDATE_MANIFEST.json"))
        for candidate in parent_manifest["candidates"]:
            candidate_id = candidate["candidate_id"]
            source = archive.read(f"candidates/{candidate_id}/candidate.py")
            parent_hash = sha256_bytes(source)
            if expected.get(candidate_id) != parent_hash:
                raise ValueError(f"parent candidate pin changed: {candidate_id}")
            try:
                normalized, normalization = normalize_source(source)
            except (NormalizationError, ValueError) as exc:
                records.append(
                    {
                        "candidate_id": candidate_id,
                        "parent_sha256": parent_hash,
                        "status": "normalization_rejected",
                        "reason": f"{type(exc).__name__}:{exc}",
                    }
                )
                continue
            normalized_hash = sha256_bytes(normalized)
            records.append(
                {
                    "candidate_id": candidate_id,
                    "stance_id": candidate["stance_id"],
                    "parent_sha256": parent_hash,
                    "normalized_sha256": normalized_hash,
                    "normalized_size_bytes": len(normalized),
                    "normalization": normalization,
                    "status": "normalized_not_executed",
                }
            )
            package_files[f"candidates/{candidate_id}/candidate.py"] = normalized

    accepted = [row for row in records if row["status"] == "normalized_not_executed"]
    package_manifest = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005c",
        "parent_package_sha256": EXPECTED_PARENT_PACKAGE_SHA256,
        "candidate_count": len(accepted),
        "candidates": accepted,
    }
    manifest_bytes = json.dumps(package_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    package_files["CANDIDATE_MANIFEST.json"] = manifest_bytes
    output_root.mkdir(parents=True)
    package_path = output_root / "NORMALIZED_CANDIDATE_PACKAGE.zip"
    deterministic_zip(package_path, package_files)
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005c",
        "status": "maintenance_normalization_feasible" if len(accepted) == 8 else "maintenance_normalization_blocker",
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "parent_package_sha256": EXPECTED_PARENT_PACKAGE_SHA256,
        "candidate_records": records,
        "accounting": {
            "parent_sources_opened": len(records),
            "normalized_candidates": len(accepted),
            "normalization_rejections": len(records) - len(accepted),
            "source_edits": len(accepted),
            "model_or_repair_inferences": 0,
            "candidate_imports": 0,
            "candidate_processes": 0,
            "oia_processes": 0,
            "step_2_or_later_payloads_read": 0,
            "real_arc_actions": 0,
            "network_or_service_calls": 0,
        },
        "package": {
            "path": "normalization-result/NORMALIZED_CANDIDATE_PACKAGE.zip",
            "sha256": sha256_file(package_path),
            "size_bytes": package_path.stat().st_size,
            "manifest_sha256": sha256_bytes(manifest_bytes),
        },
        "claim_boundary": "Deterministic missing-copy-import maintenance only; normalized sources have not been imported or executed.",
    }
    (output_root / "NORMALIZATION_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = normalize(args.output_root.resolve())
    print(
        json.dumps(
            {
                "normalized": result["accounting"]["normalized_candidates"],
                "package_sha256": result["package"]["sha256"],
                "rejected": result["accounting"]["normalization_rejections"],
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
