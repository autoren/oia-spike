from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_track_a_005a_candidates as generation


VALID_CODE = """import numpy as np

RUNNING = "RUNNING"
LEVEL_COMPLETED = "LEVEL_COMPLETED"
GAME_OVER = "GAME_OVER"

def initial_state(initial_frame):
    return {"frame": np.asarray(initial_frame).copy(), "step": 0}

def step(state, action):
    if action not in ("ACTION6", "ACTION7"):
        raise ValueError("unknown action")
    new_state = {"frame": state["frame"].copy(), "step": state["step"] + 1}
    return new_state, RUNNING

def render(state):
    return state["frame"].copy()
"""


class TrackA005aCandidateGenerationTests(unittest.TestCase):
    def test_exact_delimiters_and_valid_code_pass(self) -> None:
        response = f"{generation.BEGIN_MARKER}\n{VALID_CODE}{generation.END_MARKER}\n"
        code = generation.extract_code(response)
        validation = generation.validate_code(code)
        self.assertEqual(validation["result"], "pass")
        self.assertEqual(
            set(generation.REQUIRED_FUNCTIONS),
            set(validation["functions"]) & generation.REQUIRED_FUNCTIONS,
        )

    def test_prose_outside_delimiters_is_rejected(self) -> None:
        response = f"Here it is\n{generation.BEGIN_MARKER}\n{VALID_CODE}{generation.END_MARKER}"
        with self.assertRaisesRegex(generation.CandidateFormatError, "outside"):
            generation.extract_code(response)

    def test_forbidden_import_and_call_are_rejected(self) -> None:
        with self.assertRaisesRegex(generation.CandidateFormatError, "forbidden_import"):
            generation.validate_code("import os\n" + VALID_CODE)
        with self.assertRaisesRegex(generation.CandidateFormatError, "forbidden_call"):
            generation.validate_code(VALID_CODE.replace("return state[\"frame\"].copy()", "open('x')\n    return state[\"frame\"].copy()"))

    def test_candidate_zip_is_byte_reproducible(self) -> None:
        files = {
            "CANDIDATE_MANIFEST.json": b"{}\n",
            "candidates/C0001/candidate.py": VALID_CODE.encode(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.zip"
            right = Path(temporary) / "right.zip"
            generation.deterministic_zip(left, files)
            generation.deterministic_zip(right, files)
            self.assertEqual(left.read_bytes(), right.read_bytes())


if __name__ == "__main__":
    unittest.main()
