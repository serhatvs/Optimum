from __future__ import annotations

import random

from autochess.systems.generator import generate_character, parse_generator_config
from autochess.systems.loader import load_json


def test_generate_character_respects_aux_caps() -> None:
    cfg = parse_generator_config(load_json("data/archetypes.json"))
    rng = random.Random(99)

    character = generate_character(
        rng=rng,
        config=cfg,
        char_id="char_test_1",
        name="Test",
        tier=2,
        star_level=1,
        forced_archetype="Assassin",
    )

    aux = character.aux_stats.as_dict()
    for stat, value in aux.items():
        cap = cfg.aux_caps[stat]
        assert cap["min"] <= value <= cap["max"]
