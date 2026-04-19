from __future__ import annotations

import random

from autochess.models import BattleResult, Character


TICKS_PER_SECOND = 20
MAX_TICKS = 20 * 120


def _attack_interval(attack_speed: float) -> int:
    return max(1, int(TICKS_PER_SECOND / max(0.2, attack_speed)))


def _evade_chance(agility: float) -> float:
    return min(0.35, agility / 500.0)


def _raw_damage(atk: int, target_def: int) -> int:
    return max(1, int(atk - (target_def * 0.6)))


def run_duel(char_a: Character, char_b: Character, seed: int) -> BattleResult:
    rng = random.Random(seed)
    left = _clone_runtime(char_a)
    right = _clone_runtime(char_b)
    log: list[str] = []

    left_timer = _attack_interval(left.aux_stats.attack_speed)
    right_timer = _attack_interval(right.aux_stats.attack_speed)
    tick = 0

    for tick in range(1, MAX_TICKS + 1):
        left_timer -= 1
        right_timer -= 1

        if left_timer <= 0 and left.alive:
            _perform_attack(rng, attacker=left, defender=right, log=log, tick=tick)
            left_timer = _attack_interval(left.aux_stats.attack_speed)
        if right_timer <= 0 and right.alive:
            _perform_attack(rng, attacker=right, defender=left, log=log, tick=tick)
            right_timer = _attack_interval(right.aux_stats.attack_speed)

        if not left.alive or not right.alive:
            break

    if left.alive and not right.alive:
        return BattleResult(
            winner_id=left.char_id,
            loser_id=right.char_id,
            ticks=tick,
            winner_hp=left.current_hp,
            log=log,
        )
    if right.alive and not left.alive:
        return BattleResult(
            winner_id=right.char_id,
            loser_id=left.char_id,
            ticks=tick,
            winner_hp=right.current_hp,
            log=log,
        )

    if left.current_hp >= right.current_hp:
        return BattleResult(
            winner_id=left.char_id,
            loser_id=right.char_id,
            ticks=tick,
            winner_hp=left.current_hp,
            log=log,
        )
    return BattleResult(
        winner_id=right.char_id,
        loser_id=left.char_id,
        ticks=tick,
        winner_hp=right.current_hp,
        log=log,
    )


def _clone_runtime(character: Character) -> Character:
    cloned = Character(
        char_id=character.char_id,
        name=character.name,
        archetype=character.archetype,
        tier=character.tier,
        star_level=character.star_level,
        core_stats=character.core_stats,
        base_aux_stats=character.base_aux_stats,
        aux_stats=character.aux_stats,
        item_slots=dict(character.item_slots),
    )
    cloned.reset_runtime()
    return cloned


def _perform_attack(
    rng: random.Random,
    *,
    attacker: Character,
    defender: Character,
    log: list[str],
    tick: int,
) -> None:
    if not attacker.alive or not defender.alive:
        return
    if rng.random() < _evade_chance(defender.aux_stats.agility):
        log.append(f"t{tick}: {attacker.name} attack missed {defender.name}")
        return

    damage = _raw_damage(attacker.core_stats.atk, defender.core_stats.def_stat)
    if rng.random() < attacker.aux_stats.crit_chance:
        damage = int(damage * 1.5)
        log.append(f"t{tick}: {attacker.name} crits {defender.name} for {damage}")
    else:
        log.append(f"t{tick}: {attacker.name} hits {defender.name} for {damage}")

    defender.current_hp = max(0, defender.current_hp - damage)
    if attacker.aux_stats.lifesteal > 0:
        heal = int(damage * attacker.aux_stats.lifesteal)
        attacker.current_hp = min(
            attacker.core_stats.max_hp, attacker.current_hp + heal
        )

    if defender.current_hp <= 0:
        defender.alive = False
        log.append(f"t{tick}: {defender.name} is defeated")
