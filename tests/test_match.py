from __future__ import annotations

from types import SimpleNamespace

from autochess.models import AuxStats, Character, CoreStats, KillEvent, MatchState, Player
from autochess.systems.match import apply_arena_result, get_winner, is_match_over


def _build_player(
    player_id: str,
    name: str,
    *,
    is_human: bool,
    hp: int = 100,
    bounty: int = 0,
) -> Player:
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
        bounty=bounty,
    )


def _fake_arena_result(
    *,
    winner_id: str,
    kill_events: list[KillEvent] | None = None,
    players: list[Player],
) -> SimpleNamespace:
    return SimpleNamespace(
        winner_id=winner_id,
        kill_events=kill_events or [],
        units={
            player.player_id: SimpleNamespace(bounty=player.bounty)
            for player in players
        },
    )


def test_match_continues_when_human_is_eliminated() -> None:
    match = MatchState(
        round_number=4,
        seed=7,
        players=[
            _build_player("player_human", "Player", is_human=True, hp=12),
            _build_player("player_bot_1", "Bot-1", is_human=False, hp=80),
            _build_player("player_bot_2", "Bot-2", is_human=False, hp=56),
        ],
    )

    arena = _fake_arena_result(
        winner_id="player_bot_1",
        players=match.players,
    )
    apply_arena_result(match, arena)

    human = match.players[0]
    assert human.eliminated
    assert len(match.active_players()) == 2
    assert get_winner(match) is None
    assert not is_match_over(match)


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

    arena = _fake_arena_result(
        winner_id="player_bot_1",
        players=match.players,
    )
    events = apply_arena_result(match, arena)

    assert "Player ignores the round damage" in events
    assert match.players[0].hp == 100
    assert not match.players[0].eliminated


def test_apply_arena_result_banks_gold_and_syncs_bounty() -> None:
    match = MatchState(
        round_number=6,
        seed=9,
        players=[
            _build_player("player_human", "Player", is_human=True, hp=100, bounty=0),
            _build_player("player_bot_1", "Bot-1", is_human=False, hp=12, bounty=1),
            _build_player("player_bot_2", "Bot-2", is_human=False, hp=40, bounty=4),
            _build_player("player_bot_3", "Bot-3", is_human=False, hp=100, bounty=0),
        ],
    )
    arena = _fake_arena_result(
        winner_id="player_bot_3",
        kill_events=[
            KillEvent(
                killer_id="player_bot_1",
                victim_id="player_bot_2",
                victim_bounty_at_kill=4,
                gold_reward=50,
                bounty_gain=2,
            )
        ],
        players=match.players,
    )
    arena.units["player_bot_1"].bounty = 3
    arena.units["player_bot_2"].bounty = 2

    events = apply_arena_result(match, arena)

    assert "Bot-1 banks 50 gold from Bot-2's bounty" in events
    assert match.players[1].gold == 50
    assert match.players[1].bounty == 3
    assert match.players[2].bounty == 2
    assert match.players[1].eliminated
