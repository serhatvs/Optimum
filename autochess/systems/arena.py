from __future__ import annotations

import math
import random
from dataclasses import dataclass

from autochess.models import KillEvent, Player
from autochess.systems.bounty import (
    apply_bounty_death_penalty,
    build_kill_event,
)

ATTACK_RANGE = 34.0
RANGE_EPSILON = 1e-6
CORPSE_FADE_DURATION = 3.0
AGGRO_DISTANCE_WEIGHT = 0.90
AGGRO_BOUNTY_WEIGHT = 0.10
AGGRO_SWITCH_THRESHOLD = 0.15


@dataclass
class ArenaUnit:
    player_id: str
    name: str
    x: float
    y: float
    max_hp: int
    hp: int
    atk: int
    def_stat: int
    attack_speed: float
    agility: float
    crit_chance: float
    lifesteal: float
    bounty: int = 0
    invulnerable: bool = False
    alive: bool = True
    attack_cooldown: float = 0.0
    flash_timer: float = 0.0
    corpse_timer: float = 0.0
    target_id: str | None = None


class ArenaSimulation:
    def __init__(
        self,
        players: list[Player],
        seed: int,
        left: float,
        right: float,
        bottom: float,
        top: float,
    ) -> None:
        self.rng = random.Random(seed)
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top
        self.time_elapsed = 0.0
        self.finished = False
        self.winner_id: str | None = None
        self.kill_events: list[KillEvent] = []
        self.units = self._spawn_units(players)

    def _spawn_units(self, players: list[Player]) -> dict[str, ArenaUnit]:
        center_x = (self.left + self.right) / 2
        center_y = (self.bottom + self.top) / 2
        radius = min(self.right - self.left, self.top - self.bottom) * 0.35
        units: dict[str, ArenaUnit] = {}
        count = max(1, len(players))

        for idx, player in enumerate(players):
            angle = (2 * math.pi * idx / count) + self.rng.uniform(-0.2, 0.2)
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius
            character = player.character
            units[player.player_id] = ArenaUnit(
                player_id=player.player_id,
                name=player.name,
                x=x,
                y=y,
                max_hp=character.core_stats.max_hp,
                hp=character.core_stats.max_hp,
                atk=character.core_stats.atk,
                def_stat=character.core_stats.def_stat,
                attack_speed=max(0.2, character.aux_stats.attack_speed),
                agility=character.aux_stats.agility,
                crit_chance=character.aux_stats.crit_chance,
                lifesteal=character.aux_stats.lifesteal,
                bounty=player.bounty,
            )
        return units

    def alive_units(self) -> list[ArenaUnit]:
        return [unit for unit in self.units.values() if unit.alive]

    def _arena_diagonal(self) -> float:
        return max(1.0, math.hypot(self.right - self.left, self.top - self.bottom))

    def _target_score(
        self,
        source: ArenaUnit,
        candidate: ArenaUnit,
        *,
        highest_bounty: int,
    ) -> tuple[float, float]:
        distance = math.hypot(candidate.x - source.x, candidate.y - source.y)
        distance_score = 1.0 - min(1.0, distance / self._arena_diagonal())
        bounty_score = candidate.bounty / max(1, highest_bounty)
        total_score = (
            AGGRO_DISTANCE_WEIGHT * distance_score
            + AGGRO_BOUNTY_WEIGHT * bounty_score
        )
        return total_score, distance

    def _register_kill(
        self,
        *,
        killer: ArenaUnit,
        victim: ArenaUnit,
        events: list[str],
    ) -> None:
        kill_event = build_kill_event(
            killer_id=killer.player_id,
            victim_id=victim.player_id,
            killer_bounty=killer.bounty,
            victim_bounty=victim.bounty,
        )
        self.kill_events.append(kill_event)
        killer.bounty += kill_event.bounty_gain
        victim.bounty = apply_bounty_death_penalty(victim.bounty)
        victim.alive = False
        victim.target_id = None
        victim.corpse_timer = CORPSE_FADE_DURATION
        events.append(f"{victim.name} is down")
        events.append(
            f"{killer.name} tags +{kill_event.bounty_gain} bounty and {kill_event.gold_reward} gold"
        )

    def _advance_timers(self, delta_time: float) -> None:
        for unit in self.units.values():
            unit.flash_timer = max(0.0, unit.flash_timer - delta_time)
            if not unit.alive and unit.corpse_timer > 0:
                unit.corpse_timer = max(0.0, unit.corpse_timer - delta_time)

    def step(self, delta_time: float) -> list[str]:
        self._advance_timers(delta_time)
        if self.finished:
            return []

        events: list[str] = []
        self.time_elapsed += delta_time

        for unit in self.units.values():
            if not unit.alive:
                continue
            unit.attack_cooldown = max(0.0, unit.attack_cooldown - delta_time)

            target = self._pick_target(unit)
            unit.target_id = target.player_id if target else None
            if not target:
                continue

            dx = target.x - unit.x
            dy = target.y - unit.y
            dist = math.hypot(dx, dy)

            # Treat near-equal distances as in-range so floating point drift
            # cannot leave units permanently stuck on the attack boundary.
            if dist > ATTACK_RANGE + RANGE_EPSILON:
                move_speed = 70.0 + unit.agility * 0.9
                step_dist = min(dist - ATTACK_RANGE, move_speed * delta_time)
                if dist > 0:
                    unit.x += dx / dist * step_dist
                    unit.y += dy / dist * step_dist
                unit.x = min(self.right - 16, max(self.left + 16, unit.x))
                unit.y = min(self.top - 16, max(self.bottom + 16, unit.y))
                continue

            if unit.attack_cooldown > 0:
                continue

            if self.rng.random() < min(0.35, target.agility / 500.0):
                events.append(f"{unit.name} misses {target.name}")
                unit.attack_cooldown = max(0.15, 1.0 / unit.attack_speed)
                continue

            damage = max(1, int(unit.atk - target.def_stat * 0.6))
            if self.rng.random() < unit.crit_chance:
                damage = int(damage * 1.5)
                events.append(f"{unit.name} CRIT {target.name} for {damage}")
            else:
                events.append(f"{unit.name} hits {target.name} for {damage}")

            target.flash_timer = 0.12
            if target.invulnerable:
                events.append(f"{target.name} ignores the damage")
                unit.attack_cooldown = max(0.15, 1.0 / unit.attack_speed)
                continue

            target.hp = max(0, target.hp - damage)
            if unit.lifesteal > 0:
                heal = int(damage * unit.lifesteal)
                unit.hp = min(unit.max_hp, unit.hp + heal)

            unit.attack_cooldown = max(0.15, 1.0 / unit.attack_speed)
            if target.hp <= 0 and target.alive:
                self._register_kill(killer=unit, victim=target, events=events)

        alive = self.alive_units()
        if len(alive) <= 1 or self.time_elapsed >= 90.0:
            self.finished = True
            if alive:
                self.winner_id = alive[0].player_id
            else:
                self.winner_id = max(
                    self.units.values(),
                    key=lambda candidate: candidate.hp,
                ).player_id

        return events

    def _pick_target(self, source: ArenaUnit) -> ArenaUnit | None:
        candidates = [
            unit
            for unit in self.units.values()
            if unit.alive and unit.player_id != source.player_id
        ]
        if not candidates:
            return None

        highest_bounty = max(unit.bounty for unit in candidates)
        scored_candidates: list[tuple[ArenaUnit, float, float]] = []
        for candidate in candidates:
            score, distance = self._target_score(
                source,
                candidate,
                highest_bounty=highest_bounty,
            )
            scored_candidates.append((candidate, score, distance))

        best_candidate, best_score, _ = min(
            scored_candidates,
            key=lambda entry: (
                -entry[1],
                entry[2],
                -entry[0].bounty,
                entry[0].player_id,
            ),
        )

        current_target = self.units.get(source.target_id) if source.target_id else None
        if current_target and current_target.alive and current_target.player_id != source.player_id:
            current_score, _ = self._target_score(
                source,
                current_target,
                highest_bounty=highest_bounty,
            )
            if (
                current_target.player_id == best_candidate.player_id
                or best_score < current_score + AGGRO_SWITCH_THRESHOLD
            ):
                return current_target

        return best_candidate
