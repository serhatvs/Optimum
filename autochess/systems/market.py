from __future__ import annotations

import random

from autochess.models import Item, Player
from autochess.systems.modifiers import equip_item, recompute_aux_stats


MARKET_OFFER_COUNT = 3
MARKET_REFRESH_COST = 2
RARITY_COSTS = {
    "common": 6,
    "rare": 10,
    "epic": 14,
    "legendary": 20,
}


def get_market_price(item: Item) -> int:
    return RARITY_COSTS.get(item.rarity, 8)


def roll_market_offers(
    rng: random.Random,
    item_catalog: dict[str, Item],
    offer_count: int = MARKET_OFFER_COUNT,
) -> list[Item]:
    available_items = list(item_catalog.values())
    if not available_items:
        return []
    return rng.sample(available_items, min(offer_count, len(available_items)))


def purchase_market_item(
    *,
    player: Player,
    item: Item,
    aux_caps: dict[str, dict[str, float]],
) -> Item | None:
    price = get_market_price(item)
    if player.gold < price:
        raise ValueError("not enough gold")

    replaced_item = player.character.item_slots.get(item.slot_type)
    player.gold -= price
    equip_item(player.character, item)
    recompute_aux_stats(player.character, aux_caps)
    return replaced_item
