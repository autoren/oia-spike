"""Verify the two-layer v0.2.1 maintenance provenance model.

Historical audit artifacts and their original instrument sources are checked
against the immutable v0.2.0 archive and snapshot. Current source is checked
separately. This prevents an old freeze manifest from being silently
interpreted as if it had frozen the corrected v0.2.1 implementation.

The verifier never invokes the codec substrate. The historical ``cp437``
outcome file is compared only as immutable bytes.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_ARCHIVE = ROOT / "historical" / "OIA-1-v0.2.0-Frozen-Package.zip"
HISTORICAL_ARCHIVE_SHA256 = (
    "0c70cd82282f91a2c4a1ec61416fbbabd7ba9566ade8527253384ceb8b28c2d3"
)
ARCHIVE_PREFIX = "ontology-intervention-auditor-v0.2.0/"
AUDIT_001 = ROOT / "external" / "cpython_codecs" / "audit_001"
AUDIT_002 = ROOT / "external" / "cpython_codecs" / "audit_002"
HISTORICAL_SOURCE_ROOT = ROOT / "historical" / "v0.2.0" / "instrument_sources"
CURRENT_SOURCE_MANIFEST = ROOT / "maintenance" / "CURRENT_SOURCE_SHA256SUMS"
EXPECTED_CHANGED_FROZEN_PATHS = {"src/ontology_auditor/synthesis.py"}
EXPECTED_NESTED_MANIFEST_HASHES = {
    "external/cpython_codecs/audit_001/FREEZE_SHA256SUMS": (
        "3d1bd46cd152688ac79bad627baff05d4403ae687ac1b209f66a35c4f07bf54e"
    ),
    "external/cpython_codecs/audit_001/AUDIT_CLOSURE_SHA256SUMS": (
        "945298fd5abdbf2317206187195654a2fdf769e4efa828ef3614f88d39055b9e"
    ),
    "external/cpython_codecs/audit_002/FREEZE_SHA256SUMS": (
        "8b75abe8c474d9f75d9b4c196a51b11e511713d4970fa327b6a2cf23f7ac5e5f"
    ),
    "external/cpython_codecs/audit_002/PRE_OUTCOME_SHA256SUMS": (
        "ec74664c7fc3e1a3a311789bc91fcbbcd09de2ed1d94989df08f9a5973371489"
    ),
    "external/cpython_codecs/audit_002/FINAL_SHA256SUMS": (
        "6d475b3728a1db1f18dd740a4014906e466b9f08c74740cc37cecedcf59f7e2a"
    ),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_checksum_manifest(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        digest, relative = line.split("  ", 1)
        rows.append((digest, relative.removeprefix("./")))
    return rows


def verify_manifest(path: Path, base: Path) -> int:
    rows = parse_checksum_manifest(path)
    for expected, relative in rows:
        target = base / relative
        actual = sha256(target)
        if actual != expected:
            raise AssertionError(
                f"checksum mismatch for {target}: {actual} != {expected}"
            )
    return len(rows)


def verify_known_manifest_hashes() -> None:
    for relative, expected in EXPECTED_NESTED_MANIFEST_HASHES.items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            raise AssertionError(
                f"historical manifest changed: {relative}: {actual} != {expected}"
            )


def verify_audit_002_against_archive() -> int:
    audit_files = sorted(path for path in AUDIT_002.iterdir() if path.is_file())
    with zipfile.ZipFile(HISTORICAL_ARCHIVE) as archive:
        for path in audit_files:
            member = (
                ARCHIVE_PREFIX
                + "external/cpython_codecs/audit_002/"
                + path.name
            )
            archived = archive.read(member)
            if path.read_bytes() != archived:
                raise AssertionError(
                    f"audit_002 artifact differs from v0.2.0 archive: {path.name}"
                )
    return len(audit_files)


def load_historical_provenance() -> list[Mapping[str, object]]:
    payload = json.loads(
        (AUDIT_002 / "instrument_source_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    records = payload.get("files")
    if not isinstance(records, list):
        raise TypeError("historical instrument provenance files must be a list")
    result: list[Mapping[str, object]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError("historical instrument provenance record must be an object")
        result.append(record)
    return result


def verify_historical_sources() -> tuple[int, list[str]]:
    provenance = load_historical_provenance()
    changed_current_paths: list[str] = []
    with zipfile.ZipFile(HISTORICAL_ARCHIVE) as archive:
        for record in provenance:
            relative = str(record["path"])
            expected = str(record["sha256"])
            expected_size = int(record["size_bytes"])

            historical_path = HISTORICAL_SOURCE_ROOT / relative
            historical_bytes = historical_path.read_bytes()
            archived_bytes = archive.read(ARCHIVE_PREFIX + relative)
            if historical_bytes != archived_bytes:
                raise AssertionError(
                    f"historical source snapshot differs from archive: {relative}"
                )
            if len(historical_bytes) != expected_size:
                raise AssertionError(f"historical source size changed: {relative}")
            if sha256_bytes(historical_bytes) != expected:
                raise AssertionError(f"historical source hash changed: {relative}")

            current_path = ROOT / relative
            if sha256(current_path) != expected:
                changed_current_paths.append(relative)

    if set(changed_current_paths) != EXPECTED_CHANGED_FROZEN_PATHS:
        raise AssertionError(
            "unexpected current-vs-frozen instrument differences: "
            f"{changed_current_paths}"
        )
    return len(provenance), changed_current_paths


def verify_all() -> dict[str, object]:
    archive_hash = sha256(HISTORICAL_ARCHIVE)
    if archive_hash != HISTORICAL_ARCHIVE_SHA256:
        raise AssertionError("embedded v0.2.0 historical archive hash mismatch")

    verify_known_manifest_hashes()
    nested_counts = {
        "audit_001_freeze": verify_manifest(AUDIT_001 / "FREEZE_SHA256SUMS", AUDIT_001),
        "audit_001_closure": verify_manifest(
            AUDIT_001 / "AUDIT_CLOSURE_SHA256SUMS", AUDIT_001
        ),
        "audit_002_freeze": verify_manifest(AUDIT_002 / "FREEZE_SHA256SUMS", AUDIT_002),
        "audit_002_pre_outcome": verify_manifest(
            AUDIT_002 / "PRE_OUTCOME_SHA256SUMS", AUDIT_002
        ),
        "audit_002_final": verify_manifest(AUDIT_002 / "FINAL_SHA256SUMS", AUDIT_002),
    }
    audit_002_archive_file_count = verify_audit_002_against_archive()
    historical_source_count, changed_current_paths = verify_historical_sources()
    current_source_count = verify_manifest(CURRENT_SOURCE_MANIFEST, ROOT)

    return {
        "schema_version": 1,
        "maintenance_release": "0.2.1",
        "pass": True,
        "historical_archive": {
            "path": str(HISTORICAL_ARCHIVE.relative_to(ROOT)),
            "sha256": HISTORICAL_ARCHIVE_SHA256,
        },
        "audit_002_files_equal_to_historical_archive": audit_002_archive_file_count,
        "historical_audit_002_artifacts_mutated": False,
        "prospective_outcome_reexecuted": False,
        "prospective_outcome_handling": "immutable-byte verification only",
        "historical_source_resolution_root": str(
            HISTORICAL_SOURCE_ROOT.relative_to(ROOT)
        ),
        "historical_instrument_source_count": historical_source_count,
        "current_source_manifest": str(CURRENT_SOURCE_MANIFEST.relative_to(ROOT)),
        "current_source_count": current_source_count,
        "expected_current_differences_from_frozen_instrument": sorted(
            EXPECTED_CHANGED_FROZEN_PATHS
        ),
        "observed_current_differences_from_frozen_instrument": changed_current_paths,
        "nested_manifest_entry_counts": nested_counts,
    }


def main() -> None:
    print(json.dumps(verify_all(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
