from __future__ import annotations

from autochess.models import AuxStats, Character, CoreStats, Player
from autochess.systems.arena import ArenaSimulation


def _build_player(player_id: str, name: str, *, bounty: int = 0) -> Player:
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
    return Player(
        player_id=player_id,
        name=name,
        is_human=False,
        character=character,
        bounty=bounty,
    )


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


def test_invulnerable_units_ignore_arena_damage() -> None:
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
    bravo.invulnerable = True
    alpha.atk = 200
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 84.0
    bravo.y = 50.0

    events = arena.step(0.05)

    assert "Bravo ignores the damage" in events
    assert bravo.hp == bravo.max_hp
    assert bravo.alive


def test_kill_updates_bounty_gain_and_halves_victim_bounty() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha", bounty=1),
            _build_player("player_b", "Bravo", bounty=7),
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

    arena.step(0.05)

    assert alpha.bounty == 5
    assert bravo.bounty == 3
    assert arena.kill_events[0].victim_bounty_at_kill == 7
    assert arena.kill_events[0].bounty_gain == 4
    assert arena.kill_events[0].gold_reward == 80


def test_weighted_aggro_prefers_higher_bounty_at_same_distance() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo", bounty=0),
            _build_player("player_c", "Charlie", bounty=6),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    charlie = arena.units["player_c"]
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 90.0
    bravo.y = 50.0
    charlie.x = 50.0
    charlie.y = 90.0

    target = arena._pick_target(alpha)

    assert target is charlie


def test_weighted_aggro_can_prefer_farther_high_bounty_target() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo", bounty=0),
            _build_player("player_c", "Charlie", bounty=10),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    charlie = arena.units["player_c"]
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 60.0
    bravo.y = 50.0
    charlie.x = 130.0
    charlie.y = 50.0

    target = arena._pick_target(alpha)

    assert target is charlie


def test_sticky_aggro_keeps_current_target_for_small_score_gap() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo", bounty=0),
            _build_player("player_c", "Charlie", bounty=0),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    charlie = arena.units["player_c"]
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 85.0
    bravo.y = 50.0
    charlie.x = 70.0
    charlie.y = 50.0
    alpha.target_id = bravo.player_id

    target = arena._pick_target(alpha)

    assert target is bravo


def test_sticky_aggro_switches_for_much_better_target() -> None:
    arena = ArenaSimulation(
        players=[
            _build_player("player_a", "Alpha"),
            _build_player("player_b", "Bravo", bounty=0),
            _build_player("player_c", "Charlie", bounty=10),
        ],
        seed=7,
        left=0,
        right=200,
        bottom=0,
        top=200,
    )

    alpha = arena.units["player_a"]
    bravo = arena.units["player_b"]
    charlie = arena.units["player_c"]
    alpha.x = 50.0
    alpha.y = 50.0
    bravo.x = 85.0
    bravo.y = 50.0
    charlie.x = 110.0
    charlie.y = 50.0
    alpha.target_id = bravo.player_id

    target = arena._pick_target(alpha)

    assert target is charlie
