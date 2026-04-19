from __future__ import annotations
from autochess.models import Item, MatchState

def get_merged_item(equipped_item: Item, incoming_item: Item, match_state: MatchState) -> Item | None:
    recipe_key = tuple(sorted((equipped_item.item_id, incoming_item.item_id)))
    result_id = match_state.item_mergings.get(recipe_key)
    if result_id is None:
        return None
    
    # Return a new instance of the merged item
    base_template = match_state.item_catalog.get(result_id)
    if not base_template:
        return None
        
    return Item(
        item_id=base_template.item_id,
        name=base_template.name,
        slot_type=base_template.slot_type,
        rarity=base_template.rarity,
        modifiers=base_template.modifiers,
        unique=base_template.unique
    )
