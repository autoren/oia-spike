from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import inventory_track_a_005a_source as inventory


def synthetic_members(*, omit: tuple[str, str, str] | None = None):
    yield inventory.Member("runs_additional/", "directory", 0)
    for run in inventory.EXPECTED_RUNS:
        for game in ("aa00", "bb00", "ls20"):
            yield inventory.Member(f"runs_additional/{run}/{game}/", "directory", 0)
            for filename in inventory.P0_FILENAMES:
                if omit == (run, game, filename):
                    continue
                path = "/".join(
                    ("runs_additional", run, game)
                    + inventory.P0_PREFIX_PARTS
                    + (filename,)
                )
                yield inventory.Member(path, "file", 7)


class TrackA005aSourceInventoryTests(unittest.TestCase):
    def test_selection_is_deterministic_and_excludes_opened_game(self) -> None:
        result = inventory.inventory_members(synthetic_members(), expected_game_count=3)
        ranking = result["selection"]["ranking"]
        self.assertEqual({row["game"] for row in ranking}, {"aa00", "bb00"})
        self.assertEqual(result["selection"]["selected_game"], ranking[0]["game"])
        self.assertEqual(result["selection"]["eligible_game_count"], 2)

    def test_incomplete_p0_rejects_only_affected_game(self) -> None:
        omission = (inventory.EXPECTED_RUNS[0], "bb00", "initial_frame.txt")
        result = inventory.inventory_members(
            synthetic_members(omit=omission), expected_game_count=3
        )
        self.assertEqual([row["game"] for row in result["selection"]["ranking"]], ["aa00"])
        rejected = {row["game"]: row for row in result["selection"]["rejected"]}
        self.assertIn("incomplete_common_level_1_p0", rejected["bb00"]["reasons"])

    def test_unsafe_member_name_fails_closed(self) -> None:
        members = list(synthetic_members())
        members.append(inventory.Member("../escape", "file", 1))
        with self.assertRaisesRegex(ValueError, "unsafe tar member"):
            inventory.inventory_members(members, expected_game_count=3)


if __name__ == "__main__":
    unittest.main()
