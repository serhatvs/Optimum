from __future__ import annotations

from autochess.models import AuxStats, Character, CoreStats, Player
from autochess.systems.arena import ArenaSimulation


def _build_player(player_id: str, name: str) -> Player:
    character = Character(
        char_id=f"char_{player_id}",
        name=name,
        archetype="Hybrid",
        tier=1,
        star_level=1,
        core_stats=CoreStats(max_hp=100, atk=20, def_stat=0),
        base_aux_stats=AuxStats(
            attack_speed=1.0,
            agility=0.0,
            crit_chance=0.0,
            mana_gain=1.0,
            lifesteal=0.0,
        ),
        aux_stats=AuxStats(
            attack_speed=1.0,
            agility=0.0,
            crit_chance=0.0,
            mana_gain=1.0,
            lifesteal=0.0,
        ),
    )
    return Player(player_id=player_id, name=name, is_human=False, character=character)


def test_units_attack_when_distance_is_only_float_noise_above_range() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo"),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 84.00000000000001
    bravo.y = 50.0

    events = arena.step(0.05)

    assert events
    assert any("hits" in event for event in events)


def test_dead_units_fade_out_over_three_seconds() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo"),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    alpha.atk = 200
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 84.0
    bravo.y = 50.0

    events = arena.step(0.05)

    assert any("Bravo is down" == event for event in events)
    assert not bravo.alive
    assert bravo.corpse_timer == 3.0

    arena.step(1.0)
    assert bravo.corpse_timer == 2.0

    arena.step(2.0)
    assert bravo.corpse_timer == 0.0
