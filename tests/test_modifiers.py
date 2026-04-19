from __future__ import annotations

import random

from autochess.models import Item, Modifier
from autochess.systems.generator import (
    generate_character,
    parse_generator_config,
)
from autochess.systems.loader import load_json
from autochess.systems.modifiers import equip_item, recompute_aux_stats


def test_recompute_aux_stats_changes_values() -> None:
    cfg = parse_generator_config(load_json("data/archetypes.json"))
    rng = random.Random(123)

    character = generate_character(
        rng=rng,
        config=cfg,
        char_id="char_test_2",
        name="Test",
        tier=2,
        star_level=1,
        forced_archetype="Hybrid",
    )

    before = character.aux_stats.as_dict()
    equip_item(
        character,
        Item(
            item_id="item_test_frenzy",
            name="Test Frenzy",
            slot_type="legs",
            rarity="common",
            modifiers=[
                Modifier(
                    stat="attack_speed",
                    mode="percent",
                    value=0.22,
                    source="item_test_frenzy",
                ),
                Modifier(
                    stat="lifesteal",
                    mode="percent",
                    value=-0.08,
                    source="item_test_frenzy",
                ),
            ],
        ),
    )
    recompute_aux_stats(character, cfg.aux_caps)
    after = character.aux_stats.as_dict()

    assert after["attack_speed"] > before["attack_speed"]
    assert after["lifesteal"] < before["lifesteal"]
