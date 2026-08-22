from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import normalize_track_a_005c_candidates as normalization


VALID = b'''import numpy as np
from typing import Any

RUNNING = "RUNNING"
LEVEL_COMPLETED = "LEVEL_COMPLETED"
GAME_OVER = "GAME_OVER"

def initial_state(initial_frame):
    return {"frame": np.asarray(initial_frame).copy()}

def step(state, action):
    next_state = copy.deepcopy(state)
    return next_state, RUNNING

def render(state):
    return state["frame"].copy()
'''


class TrackA005cNormalizationTests(unittest.TestCase):
    def test_exact_missing_copy_import_is_normalized(self) -> None:
        normalized, record = normalization.normalize_source(VALID)
        self.assertEqual(normalized, b"import copy\n" + VALID)
        self.assertEqual(record["edit"], "prepend_import_copy")
        self.assertEqual(record["copy_deepcopy_use_count"], 1)
        self.assertEqual(record["other_source_bytes_changed"], 0)

    def test_existing_copy_binding_is_rejected(self) -> None:
        with self.assertRaisesRegex(normalization.NormalizationError, "already_bound"):
            normalization.normalize_source(b"import copy\n" + VALID)

    def test_other_copy_use_is_rejected(self) -> None:
        source = VALID.replace(b"copy.deepcopy(state)", b"copy.copy(state)")
        with self.assertRaisesRegex(normalization.NormalizationError, "not_exact_deepcopy"):
            normalization.normalize_source(source)

    def test_no_copy_use_is_rejected(self) -> None:
        source = VALID.replace(b"copy.deepcopy(state)", b"state.copy()")
        with self.assertRaisesRegex(normalization.NormalizationError, "no_loaded_copy"):
            normalization.normalize_source(source)


if __name__ == "__main__":
    unittest.main()
