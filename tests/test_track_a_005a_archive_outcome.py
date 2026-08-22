from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import extract_track_a_005a_archive_outcome as outcome


def add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mtime = 0
    archive.addfile(info, io.BytesIO(payload))


def synthetic_archive(path: Path) -> None:
    frame = (("0" * 64 + "\n") * 64).encode("ascii")
    with tarfile.open(path, "w:gz") as archive:
        for index, run in enumerate(outcome.RUN_ROOTS):
            action = "ACTION6" if index == 0 else "ACTION7"
            for basename in outcome.STEP1_BASENAMES:
                if basename == "step_0001_metadata.json":
                    payload = json.dumps(
                        {"action_input": {"data": {}, "id": action}, "state": "NOT_FINISHED"},
                        sort_keys=True,
                    ).encode("utf-8")
                elif basename.endswith(".txt"):
                    payload = frame
                else:
                    payload = b"synthetic-png"
                add_bytes(archive, outcome.member_path(run, basename), payload)


class TrackA005aArchiveOutcomeTests(unittest.TestCase):
    def test_header_inventory_requires_exact_step1_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "synthetic.tar.gz"
            synthetic_archive(archive)
            count, headers = outcome.header_inventory(archive)
            self.assertEqual(count, 55)
            self.assertTrue(all(len(rows) == 11 for rows in headers.values()))

    def test_synthetic_extraction_reads_only_matching_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "synthetic.tar.gz"
            destination = Path(temporary) / "outcome"
            synthetic_archive(archive)
            old_size = outcome.EXPECTED_ARCHIVE_SIZE
            old_hash = outcome.EXPECTED_ARCHIVE_SHA256
            try:
                outcome.EXPECTED_ARCHIVE_SIZE = archive.stat().st_size
                outcome.EXPECTED_ARCHIVE_SHA256 = outcome.sha256_file(archive)
                result = outcome.extract(archive, destination)
            finally:
                outcome.EXPECTED_ARCHIVE_SIZE = old_size
                outcome.EXPECTED_ARCHIVE_SHA256 = old_hash
            self.assertEqual(result["matching_run_roots"], [outcome.RUN_ROOTS[0]])
            self.assertEqual(result["access_accounting"]["step1_metadata_payloads_read"], 5)
            self.assertEqual(result["access_accounting"]["matching_action_nonmetadata_payloads_read"], 10)
            self.assertEqual(result["access_accounting"]["nonmatching_run_frame_payloads_read"], 0)
            self.assertEqual(result["access_accounting"]["later_step_payloads_read"], 0)


if __name__ == "__main__":
    unittest.main()
