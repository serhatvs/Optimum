from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from autochess.models import AUX_STATS, AuxStats, Character, CoreStats


Rarity = Literal["common", "rare", "epic", "legendary"]
ModifierMode = Literal["flat", "percent"]

RARITY_BASE_PRICES: dict[Rarity, int] = {
    "common": 10,
    "rare": 15,
    "epic": 30,
    "legendary": 75,
}

CORE_STATS = {"max_hp", "atk", "def"}
VALID_STATS = CORE_STATS.union(set(AUX_STATS))


@dataclass(frozen=True)
class ShopModifier:
    stat: str
    mode: ModifierMode
    value: float


@dataclass(frozen=True)
class ShopItem:
    item_id: str
    name: str
    slot_type: str
    rarity: Rarity
    base_price: int
    modifiers: tuple[ShopModifier, ...]


@dataclass(frozen=True)
class InventoryEntry:
    item: ShopItem
    level: int = 1


@dataclass(frozen=True)
class PurchaseResult:
    success: bool
    reason: str
    item_id: str
    spent_gold: int
    remaining_gold: int
    new_level: int | None = None


@dataclass(frozen=True)
class ComputedStats:
    core_stats: CoreStats
    aux_stats: AuxStats


def _expect_dict(raw: object, *, context: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{context} must be an object")
    return raw


def _expect_str(raw: object, *, context: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"{context} must be a string")
    return raw


def _expect_number(raw: object, *, context: str) -> float:
    if not isinstance(raw, (int, float)):
        raise ValueError(f"{context} must be a number")
    return float(raw)


def parse_shop_items(raw_data: dict, *, expected_count: int = 15) -> dict[str, ShopItem]:
    items_raw = raw_data.get("items")
    if not isinstance(items_raw, list):
        raise ValueError("shop payload must include an 'items' array")
    if len(items_raw) != expected_count:
        raise ValueError(
            f"shop must contain exactly {expected_count} items, found {len(items_raw)}"
        )

    parsed: dict[str, ShopItem] = {}
    for idx, item_raw in enumerate(items_raw):
        item_obj = _expect_dict(item_raw, context=f"items[{idx}]")
        item_id = _expect_str(item_obj.get("id"), context=f"items[{idx}].id")
        name = _expect_str(item_obj.get("name"), context=f"items[{idx}].name")
        slot_type = _expect_str(
            item_obj.get("slot_type"), context=f"items[{idx}].slot_type"
        )
        rarity_raw = _expect_str(item_obj.get("rarity"), context=f"items[{idx}].rarity")
        rarity = rarity_raw.lower()
        if rarity not in RARITY_BASE_PRICES:
            raise ValueError(f"items[{idx}].rarity has invalid value '{rarity_raw}'")

        modifiers_raw = item_obj.get("modifiers")
        if not isinstance(modifiers_raw, list) or not modifiers_raw:
            raise ValueError(f"items[{idx}].modifiers must be a non-empty array")

        modifiers: list[ShopModifier] = []
        for mod_idx, mod_raw in enumerate(modifiers_raw):
            mod_obj = _expect_dict(mod_raw, context=f"items[{idx}].modifiers[{mod_idx}]")
            stat = _expect_str(
                mod_obj.get("stat"), context=f"items[{idx}].modifiers[{mod_idx}].stat"
            )
            if stat not in VALID_STATS:
                raise ValueError(
                    f"items[{idx}].modifiers[{mod_idx}].stat has invalid value '{stat}'"
                )

            mode_raw = _expect_str(
                mod_obj.get("mode"), context=f"items[{idx}].modifiers[{mod_idx}].mode"
            )
            mode = mode_raw.lower()
            if mode not in ("flat", "percent"):
                raise ValueError(
                    f"items[{idx}].modifiers[{mod_idx}].mode has invalid value '{mode_raw}'"
                )

            value = _expect_number(
                mod_obj.get("value"), context=f"items[{idx}].modifiers[{mod_idx}].value"
            )
            modifiers.append(ShopModifier(stat=stat, mode=mode, value=value))

        if item_id in parsed:
            raise ValueError(f"duplicate item id '{item_id}' in shop payload")

        parsed[item_id] = ShopItem(
            item_id=item_id,
            name=name,
            slot_type=slot_type,
            rarity=rarity,
            base_price=RARITY_BASE_PRICES[rarity],
            modifiers=tuple(modifiers),
        )
    return parsed


@dataclass
class PlayerInventory:
    catalog: dict[str, ShopItem]
    starting_gold: int = 600
    round_limit: int = 9
    current_round: int = 1
    gold: int = field(init=False)
    items: dict[str, InventoryEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.starting_gold < 0:
            raise ValueError("starting_gold cannot be negative")
        if self.round_limit <= 0:
            raise ValueError("round_limit must be positive")
        if not (1 <= self.current_round <= self.round_limit):
            raise ValueError("current_round must be inside round_limit")
        self.gold = self.starting_gold

    def set_round(self, round_number: int) -> None:
        if not (1 <= round_number <= self.round_limit):
            raise ValueError(
                f"round_number must be between 1 and {self.round_limit}, got {round_number}"
            )
        self.current_round = round_number

    def add_item(self, item_id: str) -> PurchaseResult:
        item = self.catalog.get(item_id)
        if item is None:
            return PurchaseResult(
                success=False,
                reason="unknown_item",
                item_id=item_id,
                spent_gold=0,
                remaining_gold=self.gold,
            )

        price = item.base_price
        if self.gold < price:
            return PurchaseResult(
                success=False,
                reason="insufficient_gold",
                item_id=item_id,
                spent_gold=0,
                remaining_gold=self.gold,
            )

        self.gold -= price
        if item_id in self.items:
            entry = self.items[item_id]
            new_level = entry.level + 1
            self.items[item_id] = InventoryEntry(item=item, level=new_level)
            return PurchaseResult(
                success=True,
                reason="upgraded",
                item_id=item_id,
                spent_gold=price,
                remaining_gold=self.gold,
                new_level=new_level,
            )

        self.items[item_id] = InventoryEntry(item=item, level=1)
        return PurchaseResult(
            success=True,
            reason="added",
            item_id=item_id,
            spent_gold=price,
            remaining_gold=self.gold,
            new_level=1,
        )


@dataclass(frozen=True)
class StatCalculator:
    level_scaling: float = 0.5

    def scaled_modifier_value(self, base_value: float, level: int) -> float:
        if level <= 0:
            raise ValueError("level must be positive")
        return base_value * (1.0 + (level - 1) * self.level_scaling)

    def compute_stats(
        self,
        *,
        base_core: CoreStats,
        base_aux: AuxStats,
        inventory: PlayerInventory,
        aux_caps: dict[str, dict[str, float]] | None = None,
    ) -> ComputedStats:
        core_base = {
            "max_hp": float(base_core.max_hp),
            "atk": float(base_core.atk),
            "def": float(base_core.def_stat),
        }
        aux_base = base_aux.as_dict()

        core_flats = {key: 0.0 for key in CORE_STATS}
        core_percents = {key: 0.0 for key in CORE_STATS}
        aux_flats = {stat: 0.0 for stat in AUX_STATS}
        aux_percents = {stat: 0.0 for stat in AUX_STATS}

        for entry in inventory.items.values():
            for modifier in entry.item.modifiers:
                value = self.scaled_modifier_value(modifier.value, entry.level)
                if modifier.stat in CORE_STATS:
                    if modifier.mode == "flat":
                        core_flats[modifier.stat] += value
                    else:
                        core_percents[modifier.stat] += value
                elif modifier.stat in AUX_STATS:
                    if modifier.mode == "flat":
                        aux_flats[modifier.stat] += value
                    else:
                        aux_percents[modifier.stat] += value

        final_core: dict[str, float] = {}
        for stat in CORE_STATS:
            stat_value = core_base[stat] + core_flats[stat]
            stat_value *= 1.0 + core_percents[stat]
            final_core[stat] = stat_value

        final_aux: dict[str, float] = {}
        for stat in AUX_STATS:
            stat_value = aux_base[stat] + aux_flats[stat]
            stat_value *= 1.0 + aux_percents[stat]
            if aux_caps:
                cap = aux_caps.get(stat, {})
                if "min" in cap:
                    stat_value = max(cap["min"], stat_value)
                if "max" in cap:
                    stat_value = min(cap["max"], stat_value)
            final_aux[stat] = stat_value

        return ComputedStats(
            core_stats=CoreStats(
                max_hp=int(round(final_core["max_hp"])),
                atk=int(round(final_core["atk"])),
                def_stat=int(round(final_core["def"])),
            ),
            aux_stats=AuxStats.from_dict(final_aux),
        )

    def apply_to_character(
        self,
        *,
        character: Character,
        inventory: PlayerInventory,
        aux_caps: dict[str, dict[str, float]] | None = None,
    ) -> None:
        computed = self.compute_stats(
            base_core=character.core_stats,
            base_aux=character.base_aux_stats,
            inventory=inventory,
            aux_caps=aux_caps,
        )
        character.core_stats = computed.core_stats
        character.aux_stats = computed.aux_stats
