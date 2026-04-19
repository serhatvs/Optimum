from __future__ import annotations

import random

from autochess.models import AuxStats, Character, CoreStats, Item, ITEM_SLOTS
from autochess.systems.modifiers import recompute_aux_stats
from autochess.systems.optimizer import solve_survival_model


BUILD_SLOT_KEYS = ITEM_SLOTS
BUILD_OFFER_COUNT = 9


def roll_build_offers(
    rng: random.Random,
    item_catalog: dict[str, Item],
    *,
    offer_count: int = BUILD_OFFER_COUNT,
) -> list[Item]:
    pool = list(item_catalog.values())
    if not pool:
        return []

    shuffled = list(pool)
    rng.shuffle(shuffled)
    offers = shuffled[:offer_count]
    while len(offers) < offer_count:
        offers.append(rng.choice(pool))
    return offers


def clone_character_for_build(character: Character) -> Character:
    return Character(
        char_id=character.char_id,
        name=character.name,
        archetype=character.archetype,
        tier=character.tier,
        star_level=character.star_level,
        core_stats=CoreStats(
            max_hp=character.core_stats.max_hp,
            atk=character.core_stats.atk,
            def_stat=character.core_stats.def_stat,
        ),
        base_aux_stats=AuxStats.from_dict(character.base_aux_stats.as_dict()),
        aux_stats=AuxStats.from_dict(character.base_aux_stats.as_dict()),
        item_slots=dict(character.item_slots),
        inventory=list(character.inventory),
    )


def apply_build_selection_to_character(
    *,
    character: Character,
    selected_items: dict[str, Item | None],
    aux_caps: dict[str, dict[str, float]],
) -> None:
    for slot, item in selected_items.items():
        if slot not in BUILD_SLOT_KEYS:
            raise ValueError(f"unknown slot '{slot}'")
        if item is not None and item.slot_type != slot:
            raise ValueError(
                f"item '{item.item_id}' cannot be equipped in '{slot}' (expected '{item.slot_type}')"
            )

    character.item_slots = {
        slot: selected_items.get(slot)
        for slot in BUILD_SLOT_KEYS
    }

    # Remove newly equipped items from inventory by unique instance id
    equipped_instance_ids = {item.unique_instance_id for item in character.item_slots.values() if item}
    character.inventory = [item for item in character.inventory if item.unique_instance_id not in equipped_instance_ids]

    recompute_aux_stats(character, aux_caps)


def get_build_recommendation(
    character: Character, available_items: list[Item]
) -> dict[str, Item | None]:
    return solve_survival_model(character, available_items)
