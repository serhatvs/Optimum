from __future__ import annotations

import random

from autochess.models import AuxStats, Character, CoreStats, Item, ITEM_SLOTS
from autochess.systems.modifiers import recompute_aux_stats


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
    )


def apply_build_selection_to_character(
    *,
    character: Character,
    selected_items: dict[str, Item | None],
    aux_caps: dict[str, dict[str, float]],
) -> None:
    character.item_slots = {
        slot: selected_items.get(slot)
        for slot in BUILD_SLOT_KEYS
    }
    recompute_aux_stats(character, aux_caps)
