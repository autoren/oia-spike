#!/usr/bin/env python3
"""Generate opaque outcome-conditioned candidates with the frozen local model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Mapping

from generate_track_a_005a_candidates import (
    BEGIN_MARKER,
    END_MARKER,
    CandidateFormatError,
    deterministic_zip,
    validate_code,
    verify_model,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "audits" / "track-a-005b"
INPUT_ROOT = AUDIT_ROOT / "revision-input"
INPUT_MANIFEST_PATH = INPUT_ROOT / "REVISION_INPUT_MANIFEST.json"
PROVENANCE_PATH = ROOT / "audits" / "track-a-005a" / "GENERATION_RUNTIME_PROVENANCE.json"
PROMPT_PATH = AUDIT_ROOT / "REVISION_GENERATION_PROMPT.template.txt"
STANCES_PATH = AUDIT_ROOT / "REVISION_HYPOTHESIS_STANCES.frozen.json"
EXPECTED_MODEL_REVISION = "3e6447f082e89cc7f0bc6e5441afd38dfce760ff"
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
EXPECTED_P1_SHA256 = "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"
EXPECTED_ACTIONS = ("ACTION6", "ACTION7")
MAX_TOKENS = 2200
FENCE_RE = re.compile(r"\A\s*```(?:python)?[ \t]*\r?\n(.*?)\r?\n?```\s*\Z", re.DOTALL)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_code(code: str) -> str:
    normalized = code.strip() + "\n"
    if len(normalized.encode("utf-8")) > 40_000:
        raise CandidateFormatError("code_size")
    if not normalized.strip():
        raise CandidateFormatError("empty_code")
    return normalized


def extract_code(response: str) -> tuple[str, str]:
    """Apply the frozen marker, fence, then raw parser without repair."""
    has_marker = BEGIN_MARKER in response or END_MARKER in response
    if has_marker:
        if response.count(BEGIN_MARKER) != 1 or response.count(END_MARKER) != 1:
            raise CandidateFormatError("marker_count")
        before, remainder = response.split(BEGIN_MARKER, 1)
        code, after = remainder.split(END_MARKER, 1)
        if before.strip() or after.strip():
            raise CandidateFormatError("text_outside_markers")
        return normalize_code(code), "literal_markers"
    if "```" in response:
        if response.count("```") != 2:
            raise CandidateFormatError("fence_count")
        match = FENCE_RE.fullmatch(response)
        if match is None:
            raise CandidateFormatError("ambiguous_or_prose_fence")
        return normalize_code(match.group(1)), "single_python_or_plain_fence"
    return normalize_code(response), "raw_python"


def load_inputs() -> dict[str, object]:
    manifest = json.loads(INPUT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["audit_id"] != "OIA-1-TRACK-A-005b":
        raise ValueError("revision input audit changed")
    if manifest["p0"]["sha256"] != EXPECTED_P0_SHA256:
        raise ValueError("P0 manifest hash changed")
    if manifest["p1_settled"]["sha256"] != EXPECTED_P1_SHA256:
        raise ValueError("P1 manifest hash changed")
    if manifest["source"]["later_step_payloads_read"] != 0:
        raise ValueError("later-step boundary crossed")
    for record in (manifest["p0"], manifest["p1_settled"]):
        if sha256_file(INPUT_ROOT / record["path"]) != record["sha256"]:
            raise ValueError(f"revision input changed: {record['path']}")
    for variant in manifest["transient_variants"]:
        for frame in variant["frames"]:
            if sha256_file(INPUT_ROOT / frame["path"]) != frame["sha256"]:
                raise ValueError(f"transient input changed: {frame['path']}")
    if sorted(row["multiplicity"] for row in manifest["transient_variants"]) != [2, 3]:
        raise ValueError("transient multiplicities changed")
    return manifest


def transient_text(manifest: Mapping[str, object], variant_id: str) -> str:
    variant = next(
        row for row in manifest["transient_variants"] if row["variant_id"] == variant_id
    )
    parts = []
    for frame in variant["frames"]:
        text = (INPUT_ROOT / frame["path"]).read_text(encoding="utf-8").rstrip("\n")
        parts.append(f"Frame {frame['index']:02d}:\n{text}")
    return "\n\n".join(parts)


def render_prompt(
    template: str, stance: Mapping[str, object], manifest: Mapping[str, object]
) -> str:
    values = {
        "{{STANCE_ID}}": str(stance["stance_id"]),
        "{{STANCE_INSTRUCTION}}": str(stance["instruction"]),
        "{{CANDIDATE_ID}}": str(stance["candidate_id"]),
        "{{ACTION_NAMES}}": json.dumps(list(EXPECTED_ACTIONS), separators=(",", ":")),
        "{{P0_FRAME}}": (INPUT_ROOT / manifest["p0"]["path"]).read_text(
            encoding="utf-8"
        ).rstrip("\n"),
        "{{P1_FRAME}}": (INPUT_ROOT / manifest["p1_settled"]["path"]).read_text(
            encoding="utf-8"
        ).rstrip("\n"),
        "{{TRANSIENT_V1}}": transient_text(manifest, "V1"),
        "{{TRANSIENT_V2}}": transient_text(manifest, "V2"),
    }
    result = template
    for key, value in values.items():
        if result.count(key) < 1:
            raise ValueError(f"prompt placeholder count changed: {key}")
        result = result.replace(key, value)
    if re.search(r"\{\{[A-Z0-9_]+\}\}", result):
        raise ValueError("unresolved prompt placeholder")
    forbidden = ("su15", "article2_main_runs_additional", "step_0002")
    if any(token in result for token in forbidden):
        raise ValueError("forbidden provenance or later-step token entered prompt")
    return result


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
        raise FileExistsError("revision generation output already exists")
    output_root.mkdir(parents=True)
    (output_root / "raw-responses").mkdir()
    (output_root / "candidates").mkdir()

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    verify_model(args.snapshot.resolve(), provenance)
    manifest = load_inputs()
    template = PROMPT_PATH.read_text(encoding="utf-8")
    stances = json.loads(STANCES_PATH.read_text(encoding="utf-8"))["stances"]
    if [row["candidate_id"] for row in stances] != [f"R{index:04d}" for index in range(1, 9)]:
        raise ValueError("frozen revision stance order changed")

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    model, tokenizer = load(str(args.snapshot.resolve()))
    sampler = make_sampler(temp=0.0)
    records: list[dict[str, object]] = []
    package_files: dict[str, bytes] = {}
    for stance in stances:
        candidate_id = str(stance["candidate_id"])
        user_prompt = render_prompt(template, stance, manifest)
        messages = [
            {
                "role": "system",
                "content": (
                    "Generate one executable revised uncertainty hypothesis. "
                    "Return exactly one permitted source representation and follow the contract."
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
        raw = response.encode("utf-8")
        (output_root / "raw-responses" / f"{candidate_id}.txt").write_bytes(raw)
        record: dict[str, object] = {
            "candidate_id": candidate_id,
            "stance_id": stance["stance_id"],
            "prompt_sha256": sha256_bytes(rendered.encode("utf-8")),
            "raw_response_sha256": sha256_bytes(raw),
            "raw_response_bytes": len(raw),
            "output_token_count": len(tokenizer.encode(response, add_special_tokens=False)),
            "generation": {
                "decode": "greedy",
                "max_tokens": MAX_TOKENS,
                "repairs": 0,
                "temperature": 0.0,
            },
        }
        try:
            code, representation = extract_code(response)
            structural = validate_code(code)
        except CandidateFormatError as exc:
            record.update({"status": "rejected_structural", "reason": str(exc)})
        else:
            source = code.encode("utf-8")
            path = output_root / "candidates" / candidate_id / "candidate.py"
            path.parent.mkdir()
            path.write_bytes(source)
            record.update(
                {
                    "status": "structurally_accepted_not_executed",
                    "source_representation": representation,
                    "candidate_sha256": sha256_bytes(source),
                    "candidate_size_bytes": len(source),
                    "structural_validation": structural,
                }
            )
            package_files[f"candidates/{candidate_id}/candidate.py"] = source
        records.append(record)

    accepted = [row for row in records if row["status"] == "structurally_accepted_not_executed"]
    package_manifest = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005b",
        "model_revision": EXPECTED_MODEL_REVISION,
        "revision_input_manifest_sha256": sha256_file(INPUT_MANIFEST_PATH),
        "p0_sha256": EXPECTED_P0_SHA256,
        "p1_settled_sha256": EXPECTED_P1_SHA256,
        "candidate_count": len(accepted),
        "candidates": [
            {
                key: row[key]
                for key in (
                    "candidate_id",
                    "stance_id",
                    "source_representation",
                    "candidate_sha256",
                    "candidate_size_bytes",
                    "prompt_sha256",
                    "raw_response_sha256",
                )
            }
            for row in accepted
        ],
    }
    manifest_bytes = json.dumps(package_manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    package_files["CANDIDATE_MANIFEST.json"] = manifest_bytes
    package_path = output_root / "CANDIDATE_PACKAGE.zip"
    deterministic_zip(package_path, package_files)
    result = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005b",
        "status": "revision_generation_feasible" if len(accepted) >= 2 else "revision_generation_blocked",
        "model": {
            "repository": provenance["model"]["repository"],
            "revision": EXPECTED_MODEL_REVISION,
            "provenance_sha256": sha256_file(PROVENANCE_PATH),
        },
        "revision_input_manifest_sha256": sha256_file(INPUT_MANIFEST_PATH),
        "prompt_template_sha256": sha256_file(PROMPT_PATH),
        "stances_sha256": sha256_file(STANCES_PATH),
        "candidate_records": records,
        "accounting": {
            "requested_candidates": len(stances),
            "local_model_inferences": len(stances),
            "output_tokens_recorded": sum(int(row["output_token_count"]) for row in records),
            "structurally_accepted_candidates": len(accepted),
            "structurally_rejected_candidates": len(records) - len(accepted),
            "repair_inferences": 0,
            "candidate_processes": 0,
            "candidate_behavior_steps": 0,
            "hosted_or_api_model_calls": 0,
            "network_or_service_calls": 0,
            "oia_processes": 0,
            "step_2_or_later_payloads_read": 0,
            "real_arc_actions": 0,
        },
        "package": {
            "path": "revision-generation/CANDIDATE_PACKAGE.zip",
            "sha256": sha256_file(package_path),
            "size_bytes": package_path.stat().st_size,
            "manifest_sha256": sha256_bytes(manifest_bytes),
        },
        "claim_boundary": (
            "Opened Track A outcome-conditioned local revision and static validation only; "
            "no generated candidate was imported, calibrated, or behaviorally executed."
        ),
    }
    (output_root / "GENERATION_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "accepted": len(accepted),
                "package_sha256": result["package"]["sha256"],
                "rejected": len(records) - len(accepted),
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
