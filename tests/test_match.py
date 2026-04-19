from __future__ import annotations

from autochess.models import AuxStats, Character, CoreStats, MatchState, Player
from autochess.systems.match import apply_arena_result, get_winner, is_match_over


def _build_player(player_id: str, name: str, *, is_human: bool, hp: int = 100) -> Player:
    character = Character(
        char_id=f"char_{player_id}",
        name=name,
        archetype="Hybrid",
        tier=1,
        star_level=1,
        core_stats=CoreStats(max_hp=100, atk=20, def_stat=10),
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
        is_human=is_human,
        character=character,
        hp=hp,
    )


def test_match_ends_when_human_is_eliminated() -> None:
    match = MatchState(
        round_number=4,
        seed=7,
        players=[
            _build_player("player_human", "Player", is_human=True, hp=12),
            _build_player("player_bot_1", "Bot-1", is_human=False, hp=80),
            _build_player("player_bot_2", "Bot-2", is_human=False, hp=56),
        ],
    )

    apply_arena_result(match, winner_player_id="player_bot_1")

    human = match.players[0]
    assert human.eliminated
    assert len(match.active_players()) == 2
    assert get_winner(match) is None
    assert is_match_over(match)


def test_match_is_over_when_only_one_player_remains() -> None:
    match = MatchState(
        round_number=9,
        seed=11,
        players=[
            _build_player("player_human", "Player", is_human=True, hp=100),
            _build_player("player_bot_1", "Bot-1", is_human=False, hp=0),
        ],
    )
    match.players[1].eliminated = True

    winner = get_winner(match)

    assert winner is match.players[0]
    assert is_match_over(match)


def test_infinite_health_player_ignores_round_damage() -> None:
    match = MatchState(
        round_number=2,
        seed=5,
        players=[
            _build_player("player_human", "Player", is_human=True, hp=100),
            _build_player("player_bot_1", "Bot-1", is_human=False, hp=80),
        ],
    )
    match.players[0].infinite_health = True

    events = apply_arena_result(match, winner_player_id="player_bot_1")

    assert "Player ignores the round damage" in events
    assert match.players[0].hp == 100
    assert not match.players[0].eliminated
