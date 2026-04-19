from __future__ import annotations

import random
from dataclasses import dataclass

from autochess.models import AUX_STATS, Character, CoreStats, Item, Modifier, AuxStats


@dataclass(frozen=True)
class GeneratorConfig:
    aux_caps: dict[str, dict[str, float]]
    tier_multipliers: dict[int, dict[str, float]]
    star_multipliers: dict[int, dict[str, float]]
    archetypes: list[dict]


def parse_generator_config(raw: dict) -> GeneratorConfig:
    global_rules = raw["global_rules"]
    tier_multipliers = {int(k): v for k, v in global_rules["tier_multipliers"].items()}
    star_multipliers = {int(k): v for k, v in global_rules["star_multipliers"].items()}
    return GeneratorConfig(
        aux_caps=global_rules["aux_stat_caps"],
        tier_multipliers=tier_multipliers,
        star_multipliers=star_multipliers,
        archetypes=raw["archetypes"],
    )


def parse_items(raw_items: list[dict]) -> dict[str, Item]:
    result: dict[str, Item] = {}
    for data in raw_items:
        modifiers = [
            Modifier(
                stat=mod["stat"],
                mode=mod["mode"],
                value=float(mod["value"]),
                source=data["id"],
                unique_key=mod.get("unique_key"),
            )
            for mod in data["modifiers"]
        ]
        result[data["id"]] = Item(
            item_id=data["id"],
            name=data["name"],
            slot_type=data["slot_type"],
            rarity=data["rarity"],
            modifiers=modifiers,
            unique=bool(data.get("unique", False)),
        )
    return result


def _roll_range(rng: random.Random, bounds: list[float]) -> float:
    low, high = bounds
    return rng.uniform(low, high)


def _roll_int_range(rng: random.Random, bounds: list[int]) -> int:
    low, high = bounds
    return rng.randint(low, high)


def _pick_archetype(rng: random.Random, archetypes: list[dict]) -> dict:
    return rng.choice(archetypes)


def generate_character(
    *,
    rng: random.Random,
    config: GeneratorConfig,
    char_id: str,
    name: str,
    tier: int,
    star_level: int,
    forced_archetype: str | None = None,
) -> Character:
    archetype_data = None
    if forced_archetype:
        for candidate in config.archetypes:
            if candidate["name"] == forced_archetype:
                archetype_data = candidate
                break
        if archetype_data is None:
            raise ValueError(f"unknown archetype '{forced_archetype}'")
    else:
        archetype_data = _pick_archetype(rng, config.archetypes)

    core_ranges = archetype_data["core_ranges"]
    aux_ranges = archetype_data["aux_ranges"]

    base_hp = _roll_int_range(rng, core_ranges["max_hp"])
    base_atk = _roll_int_range(rng, core_ranges["atk"])
    base_def = _roll_int_range(rng, core_ranges["def"])

    tier_mult = config.tier_multipliers[tier]
    star_mult = config.star_multipliers[star_level]

    max_hp = int(base_hp * tier_mult["max_hp"] * star_mult["max_hp"])
    atk = int(base_atk * tier_mult["atk"] * star_mult["atk"])
    def_stat = int(base_def * tier_mult["def"] * star_mult["def"])

    aux_values: dict[str, float] = {}
    for stat in AUX_STATS:
        value = _roll_range(rng, aux_ranges[stat])
        value *= tier_mult["aux"]
        stat_cap = config.aux_caps[stat]
        value = max(stat_cap["min"], min(stat_cap["max"], value))
        aux_values[stat] = value

    return Character(
        char_id=char_id,
        name=name,
        archetype=archetype_data["name"],
        tier=tier,
        star_level=star_level,
        core_stats=CoreStats(max_hp=max_hp, atk=atk, def_stat=def_stat),
        base_aux_stats=AuxStats.from_dict(aux_values),
        aux_stats=AuxStats.from_dict(aux_values),
    )


def assign_random_items(
    rng: random.Random,
    character: Character,
    items: dict[str, Item],
    max_items: int = 5,
) -> None:
    slot_to_items: dict[str, list[Item]] = {}
    for item in items.values():
        slot_to_items.setdefault(item.slot_type, []).append(item)

    for slot in character.item_slots:
        if max_items <= 0:
            break
        available = slot_to_items.get(slot, [])
        if not available:
            continue
        if rng.random() < 0.7:
            character.item_slots[slot] = rng.choice(available)
            max_items -= 1


def draw_random_item_for_slot(
    rng: random.Random,
    items: dict[str, Item],
    *,
    slot_type: str,
) -> Item | None:
    available = [item for item in items.values() if item.slot_type == slot_type]
    if not available:
        return None
    return rng.choice(available)
