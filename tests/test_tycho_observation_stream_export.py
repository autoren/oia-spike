from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "export_tycho_observation_stream.py"
SPEC = importlib.util.spec_from_file_location("export_tycho_observation_stream", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
exporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = exporter
SPEC.loader.exec_module(exporter)


def _step(*, turn: int = 1, action: str = "ACTION1", returned=None, frame=None) -> dict:
    returned = returned or [[[1]]]
    frame = frame or returned[-1]
    return {
        "turn": turn,
        "action": action,
        "state": "GameState.NOT_FINISHED",
        "levels_completed": 0,
        "frame": frame,
        "pre_action_frame": [[0]],
        "returned_frames": returned,
        "available_actions_before": ["ACTION1", "ACTION2"],
        "reasoning": {
            "llm_calls": [],
            "tool_trace": [],
            "workspace": {"snapshot_schema": 2, "file_versions": {}},
        },
    }


def _write_record(path: Path, trace: list[dict], *, partial: bool = False) -> None:
    path.write_text(
        json.dumps({"game_id": "game-fixture", "partial": partial, "trace": trace}),
        encoding="utf-8",
    )


class TychoObservationStreamExportTests(unittest.TestCase):
    def test_exports_lossless_animation_boundary_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "game.json"
            output = root / "observations.jsonl"
            _write_record(source, [_step(returned=[[[7]], [[1]]], frame=[[1]])])
            result = exporter.export_observation_stream(source, output)
            item = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(item["returned_frames"], [[[7]], [[1]]])
            self.assertTrue(item["animation_boundary"])
            self.assertEqual(result["model_calls"], 0)
            self.assertEqual(result["environment_actions"], 0)

    def test_accepts_game_over_result_grid_from_any_returned_frame(self) -> None:
        step = _step(returned=[[[2]], [[3]]], frame=[[2]])
        step["state"] = "GameState.GAME_OVER"
        item = exporter.observation_for_step(step, 0)
        self.assertEqual(item["returned_frames"], [[[2]], [[3]]])

    def test_legacy_record_without_capture_fields_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "legacy.json"
            output = root / "observations.jsonl"
            legacy = _step()
            legacy.pop("returned_frames")
            _write_record(source, [legacy])
            with self.assertRaisesRegex(ValueError, "returned_frames missing"):
                exporter.export_observation_stream(source, output)
            self.assertFalse(output.exists())

    def test_partial_record_and_overwrite_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "game.json"
            output = root / "observations.jsonl"
            _write_record(source, [_step()], partial=True)
            with self.assertRaisesRegex(ValueError, "partial"):
                exporter.export_observation_stream(source, output)
            _write_record(source, [_step()], partial=False)
            exporter.export_observation_stream(source, output)
            with self.assertRaisesRegex(ValueError, "already exists"):
                exporter.export_observation_stream(source, output)


if __name__ == "__main__":
    unittest.main()
