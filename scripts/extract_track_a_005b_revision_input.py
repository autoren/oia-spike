#!/usr/bin/env python3
"""Derive the opened Track A 005b revision input without later-step access."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZIP = (
    ROOT
    / "audits"
    / "track-a-005a"
    / "archive-outcome"
    / "ARCHIVE_OUTCOME_EVIDENCE.zip"
)
P0_PATH = ROOT / "audits" / "track-a-005a" / "p0" / "initial_frame.txt"
EXPECTED_SOURCE_SHA256 = "e6de7cd8db997c561cfb4be078cc3437347af90f9c59e402761c7d790e3ed3a4"
EXPECTED_P0_SHA256 = "1e70d7b4ccd5c1ef1e03427d90f7295cdf461583efa978f285b55755e7a915a6"
EXPECTED_SETTLED_SHA256 = "80a2fd9a8813b7ee5cd6d63a3199ffc247119b39ab60b90709696b47ec58c140"
STEP1_RE = re.compile(
    r"^runs/([^/]+)/step_0001_(metadata\.json|intermediate_(\d\d)\.txt|final\.txt)$"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def pretty_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def sequence_sha256(frames: tuple[bytes, ...]) -> str:
    framed = b"".join(len(frame).to_bytes(8, "big") + frame for frame in frames)
    return sha256_bytes(framed)


def load_opened_step1() -> dict[str, dict[str, bytes]]:
    if sha256_file(SOURCE_ZIP) != EXPECTED_SOURCE_SHA256:
        raise ValueError("opened step-1 evidence package changed")
    records: dict[str, dict[str, bytes]] = defaultdict(dict)
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        infos = archive.infolist()
        if len(infos) != len({info.filename for info in infos}):
            raise ValueError("duplicate evidence paths")
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("unsafe evidence path")
            match = STEP1_RE.fullmatch(info.filename)
            if match is None:
                # The committed evidence ZIP is step 1 only; reject any other step.
                if re.search(r"/step_(?!0001_)\d{4}_", info.filename):
                    raise ValueError(f"non-step-1 payload present: {info.filename}")
                continue
            run, kind, intermediate = match.groups()
            key = f"intermediate_{intermediate}.txt" if intermediate else kind
            records[run][key] = archive.read(info)
    expected_keys = {
        "metadata.json",
        "intermediate_00.txt",
        "intermediate_01.txt",
        "intermediate_02.txt",
        "intermediate_03.txt",
        "final.txt",
    }
    if len(records) != 5 or any(set(record) != expected_keys for record in records.values()):
        raise ValueError("opened step-1 record accounting changed")
    return dict(records)


def extract(destination: Path) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(f"destination exists: {destination}")
    p0 = P0_PATH.read_bytes()
    if sha256_bytes(p0) != EXPECTED_P0_SHA256:
        raise ValueError("P0 changed")
    records = load_opened_step1()
    final_hashes = Counter(sha256_bytes(record["final.txt"]) for record in records.values())
    if final_hashes != Counter({EXPECTED_SETTLED_SHA256: 5}):
        raise ValueError("settled step-1 replication changed")
    for record in records.values():
        metadata = json.loads(record["metadata.json"])
        if (
            metadata["action_input"]["id"] != "ACTION6"
            or metadata["state"] != "NOT_FINISHED"
            or metadata["step_index"] != 1
            or metadata["available_actions"] != [6, 7]
        ):
            raise ValueError("opened step-1 metadata boundary changed")

    sequences: dict[str, tuple[bytes, ...]] = {}
    memberships: Counter[str] = Counter()
    member_hashes: dict[str, list[str]] = defaultdict(list)
    for run, record in records.items():
        frames = tuple(record[f"intermediate_{index:02d}.txt"] for index in range(4))
        digest = sequence_sha256(frames)
        sequences.setdefault(digest, frames)
        memberships[digest] += 1
        member_hashes[digest].append(sha256_bytes(run.encode("utf-8")))
    if sorted(memberships.values()) != [2, 3]:
        raise ValueError("transient replicate multiplicities changed")

    destination.mkdir(parents=True)
    (destination / "p0.txt").write_bytes(p0)
    settled = next(iter(records.values()))["final.txt"]
    (destination / "p1_settled.txt").write_bytes(settled)
    files = ["p0.txt", "p1_settled.txt"]
    variants = []
    for variant_index, digest in enumerate(sorted(sequences), start=1):
        variant_id = f"V{variant_index}"
        frame_records = []
        for frame_index, frame in enumerate(sequences[digest]):
            relative = f"{variant_id}/intermediate_{frame_index:02d}.txt"
            path = destination / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(frame)
            files.append(relative)
            frame_records.append(
                {"index": frame_index, "path": relative, "sha256": sha256_bytes(frame)}
            )
        variants.append(
            {
                "variant_id": variant_id,
                "sequence_sha256": digest,
                "multiplicity": memberships[digest],
                "source_record_id_sha256": sorted(member_hashes[digest]),
                "frames": frame_records,
            }
        )

    manifest = {
        "schema_version": 1,
        "audit_id": "OIA-1-TRACK-A-005b",
        "source": {
            "opened_step1_evidence_sha256": EXPECTED_SOURCE_SHA256,
            "record_count": 5,
            "later_step_payloads_read": 0,
        },
        "action": "ACTION6",
        "normalized_status": "RUNNING",
        "p0": {"path": "p0.txt", "sha256": EXPECTED_P0_SHA256},
        "p1_settled": {
            "path": "p1_settled.txt",
            "sha256": EXPECTED_SETTLED_SHA256,
            "replicate_count": 5,
        },
        "transient_variants": variants,
        "prompt_boundary": {
            "includes_both_opened_transient_variants": True,
            "transients_are_qualitative_not_calibration_targets": True,
            "excluded": [
                "game_id",
                "archive_path",
                "run_labels",
                "source_model_labels",
                "click_coordinates",
                "scores",
                "step_2_or_later",
            ],
        },
    }
    manifest_bytes = pretty_bytes(manifest)
    (destination / "REVISION_INPUT_MANIFEST.json").write_bytes(manifest_bytes)
    files.append("REVISION_INPUT_MANIFEST.json")
    result = {
        "destination": destination.as_posix(),
        "file_count": len(files),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "transient_variant_multiplicities": sorted(memberships.values()),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.destination.resolve()), sort_keys=True))


if __name__ == "__main__":
    main()
