from __future__ import annotations

import random

import pytest

from autochess.systems.generator import generate_character, parse_generator_config, parse_items
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


def test_parse_items_rejects_invalid_slot_type() -> None:
    raw = load_json("data/items.json")["items"]
    raw[0]["slot_type"] = "feet"

    with pytest.raises(ValueError, match="invalid slot_type"):
        parse_items(raw)
