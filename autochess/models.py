from __future__ import annotations
import uuid

from dataclasses import dataclass, field
from typing import Optional



AUX_STATS = ("attack_speed", "agility", "crit_chance", "mana_gain", "lifesteal")
ITEM_SLOTS = ("legs", "arms", "eyes", "body", "heart", "brain")


@dataclass(frozen=True)
class Modifier:
    stat: str
    mode: str
    value: float
    source: str
    unique_key: Optional[str] = None


@dataclass(frozen=True)
class Item:
    item_id: str
    name: str
    slot_type: str
    rarity: str
    modifiers: list[Modifier]
    unique: bool = False
    unique_instance_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class CoreStats:
    max_hp: int
    atk: int
    def_stat: int


@dataclass
class AuxStats:
    attack_speed: float
    agility: float
    crit_chance: float
    mana_gain: float
    lifesteal: float

    def as_dict(self) -> dict[str, float]:
        return {
            "attack_speed": self.attack_speed,
            "agility": self.agility,
            "crit_chance": self.crit_chance,
            "mana_gain": self.mana_gain,
            "lifesteal": self.lifesteal,
        }

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> "AuxStats":
        return cls(
            attack_speed=float(values["attack_speed"]),
            agility=float(values["agility"]),
            crit_chance=float(values["crit_chance"]),
            mana_gain=float(values["mana_gain"]),
            lifesteal=float(values["lifesteal"]),
        )


@dataclass
class Character:
    char_id: str
    name: str
    archetype: str
    tier: int
    star_level: int
    core_stats: CoreStats
    base_aux_stats: AuxStats
    aux_stats: AuxStats
    item_slots: dict[str, Optional[Item]] = field(
        default_factory=lambda: {slot: None for slot in ITEM_SLOTS}
    )
    inventory: list[Item] = field(default_factory=list)
    current_hp: int = 0
    mana: float = 0.0
    alive: bool = True

    def __post_init__(self) -> None:
        if not self.current_hp:
            self.current_hp = self.core_stats.max_hp
        if self.aux_stats is None:
            self.aux_stats = AuxStats.from_dict(self.base_aux_stats.as_dict())

    def equipped_items(self) -> list[Item]:
        return [item for item in self.item_slots.values() if item is not None]

    def reset_runtime(self) -> None:
        self.current_hp = self.core_stats.max_hp
        self.mana = 0.0
        self.alive = True


@dataclass
class Player:
    player_id: str
    name: str
    is_human: bool
    character: Character
    hp: int = 100
    gold: int = 0
    bounty: int = 0
    eliminated: bool = False
    infinite_health: bool = False


@dataclass
class KillEvent:
    killer_id: str
    victim_id: str
    victim_bounty_at_kill: int
    gold_reward: int
    bounty_gain: int


@dataclass
class BattleResult:
    winner_id: str
    loser_id: str
    ticks: int
    winner_hp: int
    log: list[str]


@dataclass
class MatchState:
    round_number: int
    seed: int
    players: list[Player]
    item_catalog: dict[str, Item] = field(default_factory=dict)
    item_mergings: dict[tuple[str, str], str] = field(default_factory=dict)
    aux_caps: dict[str, dict[str, float]] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def active_players(self) -> list[Player]:
        return [player for player in self.players if not player.eliminated]
