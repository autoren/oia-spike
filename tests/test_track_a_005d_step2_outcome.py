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

import extract_track_a_005d_step2_outcome as outcome


def add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mtime = 0
    archive.addfile(info, io.BytesIO(payload))


def synthetic_archive(path: Path) -> bytes:
    frame = (("0" * 64 + "\n") * 64).encode("ascii")
    with tarfile.open(path, "w:gz") as archive:
        for index, run in enumerate(outcome.RUN_ROOTS):
            action = "ACTION7" if index == 2 else "ACTION6"
            for basename in outcome.EXPECTED_BASENAMES[run]:
                if basename == "step_0002_metadata.json":
                    payload = json.dumps(
                        {"action_input": {"data": {}, "id": action}, "state": "NOT_FINISHED"},
                        sort_keys=True,
                    ).encode("utf-8")
                elif basename.endswith(".txt"):
                    payload = frame
                else:
                    payload = b"synthetic-png"
                add_bytes(archive, outcome.member_path(run, basename), payload)
    return frame


class TrackA005dStep2OutcomeTests(unittest.TestCase):
    def test_header_inventory_preserves_variable_animation_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "synthetic.tar.gz"
            synthetic_archive(archive)
            count, headers = outcome.header_inventory(archive)
            self.assertEqual(count, 47)
            self.assertEqual([len(headers[run]) for run in outcome.RUN_ROOTS], [11, 11, 3, 11, 11])

    def test_extraction_reads_only_matching_short_run_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "synthetic.tar.gz"
            destination = Path(temporary) / "outcome"
            frame = synthetic_archive(archive)
            frame_hash = outcome.validate_frame(frame)
            old_size = outcome.EXPECTED_ARCHIVE_SIZE
            old_hash = outcome.EXPECTED_ARCHIVE_SHA256
            old_predictions = outcome.candidate_predictions
            try:
                outcome.EXPECTED_ARCHIVE_SIZE = archive.stat().st_size
                outcome.EXPECTED_ARCHIVE_SHA256 = outcome.sha256_file(archive)
                outcome.candidate_predictions = lambda: {
                    "R0001": {"final_frame_sha256": frame_hash, "status": "RUNNING"},
                    "R0005": {"final_frame_sha256": "1" * 64, "status": "RUNNING"},
                    "R0006": {"final_frame_sha256": "2" * 64, "status": "RUNNING"},
                }
                result = outcome.extract(archive, destination)
            finally:
                outcome.EXPECTED_ARCHIVE_SIZE = old_size
                outcome.EXPECTED_ARCHIVE_SHA256 = old_hash
                outcome.candidate_predictions = old_predictions
            self.assertEqual(result["matching_run_roots"], [outcome.RUN_ROOTS[2]])
            self.assertEqual(result["gate_verdict"], "revised_step2_matches_one_candidate")
            self.assertEqual(result["outcomes"][0]["intermediate_frame_pairs_preserved"], 0)
            self.assertEqual(result["access_accounting"]["step2_metadata_payloads_read"], 5)
            self.assertEqual(result["access_accounting"]["matching_action_nonmetadata_payloads_read"], 2)
            self.assertEqual(result["access_accounting"]["nonmatching_run_frame_payloads_read"], 0)
            self.assertEqual(result["access_accounting"]["step3_or_later_payloads_read"], 0)


if __name__ == "__main__":
    unittest.main()
