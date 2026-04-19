from __future__ import annotations

from collections import defaultdict

from autochess.models import AUX_STATS, Character, Item, Modifier


def _collect_modifiers(character: Character) -> list[Modifier]:
    seen_unique: set[str] = set()
    merged: list[Modifier] = []
    for item in character.equipped_items():
        _append_item_modifiers(merged, item, seen_unique)
    return merged


def _append_item_modifiers(
    target: list[Modifier], item: Item, seen_unique: set[str]
) -> None:
    for modifier in item.modifiers:
        key = modifier.unique_key or (item.item_id if item.unique else None)
        if key and key in seen_unique:
            continue
        if key:
            seen_unique.add(key)
        target.append(modifier)


def recompute_aux_stats(
    character: Character, caps: dict[str, dict[str, float]]
) -> None:
    base = character.base_aux_stats.as_dict()
    flats = defaultdict(float)
    percents = defaultdict(float)

    for modifier in _collect_modifiers(character):
        if modifier.stat not in AUX_STATS:
            continue
        if modifier.mode == "flat":
            flats[modifier.stat] += modifier.value
        elif modifier.mode == "percent":
            percents[modifier.stat] += modifier.value

    result: dict[str, float] = {}
    for stat in AUX_STATS:
        value = base[stat] + flats[stat]
        value *= 1.0 + percents[stat]
        stat_cap = caps.get(stat, {})
        if "min" in stat_cap:
            value = max(stat_cap["min"], value)
        if "max" in stat_cap:
            value = min(stat_cap["max"], value)
        result[stat] = value

    character.aux_stats = character.aux_stats.from_dict(result)


def equip_item(character: Character, item: Item) -> None:
    character.item_slots[item.slot_type] = item
