from __future__ import annotations

import unittest

from scripts.prepare_track_a_003b_admission import static_scan
from scripts.run_track_a_003b_admission import behavior_projection, frozen_words


class TrackA003bAdmissionTests(unittest.TestCase):
    def test_frozen_words_have_exact_order_and_count(self) -> None:
        words = frozen_words()
        self.assertEqual(len(words), 84)
        self.assertEqual(words[:5], [["ACTION1"], ["ACTION2"], ["ACTION3"], ["ACTION4"], ["ACTION1", "ACTION1"]])
        self.assertEqual(words[-1], ["ACTION4", "ACTION4", "ACTION4"])
        self.assertEqual(len({tuple(word) for word in words}), 84)

    def test_static_scan_rejects_forbidden_import(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden static imports"):
            static_scan({"world_model_engine.py": b"import requests\n"})

    def test_behavior_projection_excludes_runtime_diagnostics(self) -> None:
        result = {
            "status": "pass",
            "p0": {"matches_frame": True},
            "word": ["ACTION1"],
            "steps": [],
            "file_accesses": ["candidate/world_model_engine.py"],
            "emissions": {"stdout_bytes": 0},
        }
        self.assertNotIn("file_accesses", behavior_projection(result))
        self.assertNotIn("emissions", behavior_projection(result))


if __name__ == "__main__":
    unittest.main()
