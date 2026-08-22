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

import extract_track_a_005a_p0 as extractor


def valid_values() -> dict[tuple[str, str], bytes]:
    metadata = json.dumps(
        {
            "action_input": {"data": {}, "id": "RESET"},
            "available_actions": [1, 2, 3, 4],
            "step_index": 0,
        },
        sort_keys=True,
    ).encode()
    payloads = {
        "initial_frame.png": b"\x89PNG\r\n\x1a\nsynthetic",
        "initial_frame.txt": b"000\n111\n",
        "initial_metadata.json": metadata,
    }
    return {
        (run, filename): payload
        for run in extractor.EXPECTED_RUNS
        for filename, payload in payloads.items()
    }


class TrackA005aP0ExtractionTests(unittest.TestCase):
    def test_common_reset_packet_passes(self) -> None:
        canonical, validation = extractor.validate_common_p0(valid_values())
        self.assertEqual(set(canonical), set(extractor.P0_FILENAMES))
        self.assertEqual(validation["content_validation"]["frame_text"]["width"], 3)
        self.assertTrue(
            all(
                row["all_five_byte_identical"]
                for row in validation["file_equality"].values()
            )
        )

    def test_cross_run_difference_fails_closed(self) -> None:
        values = valid_values()
        values[(extractor.EXPECTED_RUNS[-1], "initial_frame.txt")] = b"222\n333\n"
        with self.assertRaisesRegex(ValueError, "differs across runs"):
            extractor.validate_common_p0(values)

    def test_reader_reads_only_exact_targets(self) -> None:
        values = valid_values()
        targets = {
            f"root/{run}/{filename}": (run, filename)
            for run in extractor.EXPECTED_RUNS
            for filename in extractor.P0_FILENAMES
        }
        with tempfile.TemporaryDirectory() as temporary:
            archive_path = Path(temporary) / "synthetic.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                for name, key in targets.items():
                    data = values[key]
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                extra = b"must-not-be-returned"
                info = tarfile.TarInfo("root/private/trace.json")
                info.size = len(extra)
                archive.addfile(info, io.BytesIO(extra))
            observed = extractor.read_exact_targets(archive_path, targets)
        self.assertEqual(observed, values)
        self.assertNotIn(b"must-not-be-returned", observed.values())


if __name__ == "__main__":
    unittest.main()
