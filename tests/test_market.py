from __future__ import annotations

import random

from autochess.models import Player
from autochess.systems.generator import (
    generate_character,
    parse_generator_config,
    parse_items,
)
from autochess.systems.loader import load_json
from autochess.systems.market import get_market_price, purchase_market_item, roll_market_offers


def _build_player() -> tuple[Player, dict[str, dict[str, float]], dict[str, object]]:
    cfg = parse_generator_config(load_json("data/archetypes.json"))
    items = parse_items(load_json("data/items.json")["items"])
    character = generate_character(
        rng=random.Random(11),
        config=cfg,
        char_id="char_market",
        name="Market Hero",
        tier=2,
        star_level=1,
        forced_archetype="Hybrid",
    )
    player = Player(
        player_id="player_human",
        name="Player",
        is_human=True,
        character=character,
        gold=40,
    )
    return player, cfg.aux_caps, items


def test_roll_market_offers_is_deterministic() -> None:
    _, _, items = _build_player()

    first = [
        item.item_id
        for item in roll_market_offers(random.Random(77), items)
    ]
    second = [
        item.item_id
        for item in roll_market_offers(random.Random(77), items)
    ]

    assert first == second
    assert len(first) == 3


def test_purchase_market_item_spends_gold_and_equips_data_slot_item() -> None:
    player, aux_caps, items = _build_player()
    item = items["item_glass_chitin"]
    before = player.character.aux_stats.as_dict()

    replaced_item = purchase_market_item(
        player=player,
        item=item,
        aux_caps=aux_caps,
    )
    after = player.character.aux_stats.as_dict()

    assert replaced_item is None
    assert player.gold == 40 - get_market_price(item)
    assert player.character.item_slots["body"] is item
    assert after["attack_speed"] > before["attack_speed"]
    assert after["lifesteal"] < before["lifesteal"]
