from __future__ import annotations

import random

from autochess.systems.generator import (
    generate_character,
    parse_generator_config,
    parse_items,
)
from autochess.systems.loader import load_json
from autochess.systems.modifiers import equip_item, recompute_aux_stats


def test_recompute_aux_stats_changes_values() -> None:
    cfg = parse_generator_config(load_json("data/archetypes.json"))
    items = parse_items(load_json("data/items.json")["items"])
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
    equip_item(character, items["item_frenzy_dagger"])
    recompute_aux_stats(character, cfg.aux_caps)
    after = character.aux_stats.as_dict()

    assert after["attack_speed"] > before["attack_speed"]
    assert after["lifesteal"] < before["lifesteal"]
