from __future__ import annotations

import random

import pytest

from autochess.models import ITEM_SLOTS
from autochess.systems.build_phase import (
    BUILD_OFFER_COUNT,
    BUILD_SLOT_KEYS,
    apply_build_selection_to_character,
    clone_character_for_build,
    roll_build_offers,
)
from autochess.systems.generator import generate_character, parse_generator_config, parse_items
from autochess.systems.loader import load_json


def _build_character():
    cfg = parse_generator_config(load_json("data/archetypes.json"))
    items = parse_items(load_json("data/items.json")["items"])
    character = generate_character(
        rng=random.Random(21),
        config=cfg,
        char_id="char_build",
        name="Builder",
        tier=2,
        star_level=1,
        forced_archetype="Hybrid",
    )
    return character, cfg.aux_caps, items


def test_roll_build_offers_fills_three_by_three_grid() -> None:
    _character, _aux_caps, items = _build_character()

    offers = roll_build_offers(random.Random(7), items)

    assert len(offers) == BUILD_OFFER_COUNT
    assert all(item.slot_type in ITEM_SLOTS for item in offers)


def test_apply_build_selection_to_character_writes_exact_slot_mapping() -> None:
    character, aux_caps, items = _build_character()
    preview = clone_character_for_build(character)
    selected_items = {
        "legs": items["item_frenzy_tendons"],
        "arms": items["item_razor_claws"],
        "eyes": items["item_hunter_eyes"],
        "body": items["item_glass_chitin"],
        "heart": items["item_ardent_heart"],
        "brain": items["item_silent_cortex"],
    }

    apply_build_selection_to_character(
        character=preview,
        selected_items=selected_items,
        aux_caps=aux_caps,
    )

    assert tuple(preview.item_slots) == BUILD_SLOT_KEYS
    for slot, item in selected_items.items():
        assert preview.item_slots[slot] is item


def test_apply_build_selection_to_character_clears_unselected_slots() -> None:
    character, aux_caps, items = _build_character()
    character.item_slots["legs"] = items["item_frenzy_tendons"]
    character.item_slots["body"] = items["item_glass_chitin"]
    preview = clone_character_for_build(character)

    apply_build_selection_to_character(
        character=preview,
        selected_items={"heart": items["item_ardent_heart"]},
        aux_caps=aux_caps,
    )

    assert preview.item_slots["heart"] is items["item_ardent_heart"]
    assert preview.item_slots["legs"] is None
    assert preview.item_slots["body"] is None


def test_clone_character_for_build_copies_inventory() -> None:
    character, _aux_caps, items = _build_character()
    bag_item = items["item_frenzy_tendons"]
    character.inventory.append(bag_item)

    preview = clone_character_for_build(character)

    assert preview.inventory == [bag_item]


def test_apply_build_selection_to_character_rejects_invalid_slot() -> None:
    character, aux_caps, items = _build_character()
    preview = clone_character_for_build(character)

    with pytest.raises(ValueError, match="unknown slot"):
        apply_build_selection_to_character(
            character=preview,
            selected_items={"feet": items["item_frenzy_tendons"]},
            aux_caps=aux_caps,
        )


def test_apply_build_selection_to_character_rejects_slot_mismatch() -> None:
    character, aux_caps, items = _build_character()
    preview = clone_character_for_build(character)

    with pytest.raises(ValueError, match="cannot be equipped"):
        apply_build_selection_to_character(
            character=preview,
            selected_items={"heart": items["item_frenzy_tendons"]},
            aux_caps=aux_caps,
        )
