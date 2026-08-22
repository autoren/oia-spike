from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import extract_track_a_005b_revision_input as extraction
import generate_track_a_005b_candidates as generation


VALID_CODE = '''import numpy as np

RUNNING = "RUNNING"
LEVEL_COMPLETED = "LEVEL_COMPLETED"
GAME_OVER = "GAME_OVER"

def initial_state(initial_frame):
    return {"frame": np.asarray(initial_frame).copy(), "step": 0}

def step(state, action):
    if action not in ("ACTION6", "ACTION7"):
        raise ValueError("unknown action")
    next_state = {"frame": state["frame"].copy(), "step": state["step"] + 1}
    return next_state, RUNNING

def render(state):
    return state["frame"].copy()
'''


class TrackA005bRevisionGenerationTests(unittest.TestCase):
    def test_three_source_representations_are_accepted(self) -> None:
        examples = (
            (
                f"{generation.BEGIN_MARKER}\n{VALID_CODE}{generation.END_MARKER}\n",
                "literal_markers",
            ),
            (f"```python\n{VALID_CODE}```\n", "single_python_or_plain_fence"),
            (VALID_CODE, "raw_python"),
        )
        for response, expected in examples:
            with self.subTest(expected):
                source, representation = generation.extract_code(response)
                self.assertEqual(representation, expected)
                self.assertEqual(generation.validate_code(source)["result"], "pass")

    def test_prose_or_ambiguous_representations_are_rejected(self) -> None:
        invalid = (
            f"prose\n{generation.BEGIN_MARKER}\n{VALID_CODE}{generation.END_MARKER}",
            f"```python\n{VALID_CODE}```\nprose",
            f"```python\n{VALID_CODE}```\n```python\n{VALID_CODE}```",
        )
        for response in invalid:
            with self.subTest(response=response[:20]):
                with self.assertRaises(generation.CandidateFormatError):
                    generation.extract_code(response)

    def test_raw_prose_fails_static_validation_without_repair(self) -> None:
        source, representation = generation.extract_code("Here is the candidate")
        self.assertEqual(representation, "raw_python")
        with self.assertRaisesRegex(generation.CandidateFormatError, "syntax_error"):
            generation.validate_code(source)

    def test_opened_input_extraction_is_reproducible_and_step1_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            left = extraction.extract(first)
            right = extraction.extract(second)
            self.assertEqual(left["manifest_sha256"], right["manifest_sha256"])
            self.assertEqual(left["transient_variant_multiplicities"], [2, 3])
            self.assertEqual(
                (first / "REVISION_INPUT_MANIFEST.json").read_bytes(),
                (second / "REVISION_INPUT_MANIFEST.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
