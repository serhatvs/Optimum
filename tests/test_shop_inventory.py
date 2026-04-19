from __future__ import annotations

import pytest

from autochess.models import AuxStats, CoreStats
from autochess.systems.loader import load_json
from autochess.systems.shop import PlayerInventory, StatCalculator, parse_shop_items


def test_parse_shop_items_assigns_base_prices_and_count() -> None:
    raw = load_json("data/items.json")
    catalog = parse_shop_items(raw)

    assert len(catalog) == 15
    assert catalog["item_frenzy_tendons"].base_price == 10
    assert catalog["item_ardent_heart"].base_price == 15
    assert catalog["item_timeworn_core"].base_price == 30
    assert catalog["item_vampire_heart"].base_price == 75


def test_add_item_upgrades_existing_entry_at_same_price() -> None:
    raw = load_json("data/items.json")
    inventory = PlayerInventory(catalog=parse_shop_items(raw), starting_gold=100)

    first = inventory.add_item("item_frenzy_tendons")
    second = inventory.add_item("item_frenzy_tendons")

    assert first.success is True
    assert second.success is True
    assert first.spent_gold == second.spent_gold == 10
    assert len(inventory.items) == 1
    assert inventory.items["item_frenzy_tendons"].level == 2
    assert inventory.gold == 80


def test_add_item_reverts_when_gold_is_insufficient() -> None:
    raw = load_json("data/items.json")
    inventory = PlayerInventory(catalog=parse_shop_items(raw), starting_gold=9)

    result = inventory.add_item("item_frenzy_tendons")

    assert result.success is False
    assert result.reason == "insufficient_gold"
    assert result.spent_gold == 0
    assert inventory.gold == 9
    assert "item_frenzy_tendons" not in inventory.items


def test_stat_calculator_scales_modifiers_by_item_level() -> None:
    raw = load_json("data/items.json")
    inventory = PlayerInventory(catalog=parse_shop_items(raw), starting_gold=100)
    inventory.add_item("item_frenzy_tendons")
    inventory.add_item("item_frenzy_tendons")
    inventory.add_item("item_frenzy_tendons")

    calculator = StatCalculator(level_scaling=0.5)
    computed = calculator.compute_stats(
        base_core=CoreStats(max_hp=100, atk=20, def_stat=10),
        base_aux=AuxStats(
            attack_speed=1.0,
            agility=0.2,
            crit_chance=0.1,
            mana_gain=1.0,
            lifesteal=0.05,
        ),
        inventory=inventory,
    )

    assert round(computed.aux_stats.attack_speed, 2) == 1.44
    assert round(computed.aux_stats.lifesteal, 2) == 0.04


def test_parse_shop_items_rejects_invalid_slot_type() -> None:
    raw = load_json("data/items.json")
    raw["items"][0]["slot_type"] = "feet"

    with pytest.raises(ValueError, match="slot_type has invalid value"):
        parse_shop_items(raw)
