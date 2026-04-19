from __future__ import annotations

from pathlib import Path

from autochess.bootstrap import build_match


def test_build_match_gives_human_one_random_body_item() -> None:
    match = build_match(seed=1337, data_dir=Path("data"))

    human = next(player for player in match.players if player.is_human)
    equipped = human.character.equipped_items()

    assert len(equipped) == 1
    assert equipped[0].slot_type == "body"
    assert human.character.item_slots["body"] is equipped[0]
