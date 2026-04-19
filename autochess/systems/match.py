from __future__ import annotations

import random

from autochess.models import KillEvent, MatchState, Player
from autochess.systems.arena import ArenaSimulation
from autochess.systems.bounty import (
    apply_bounty_death_penalty,
    build_kill_event,
)
from autochess.systems.combat import run_duel


ROUND_LOSS_DAMAGE = 12


def player_has_infinite_health(player: Player) -> bool:
    return player.infinite_health


def _players_by_id(match: MatchState) -> dict[str, Player]:
    return {player.player_id: player for player in match.players}


def _apply_kill_rewards(
    *,
    players_by_id: dict[str, Player],
    kill_events: list[KillEvent],
    events: list[str],
) -> None:
    for kill_event in kill_events:
        killer = players_by_id.get(kill_event.killer_id)
        victim = players_by_id.get(kill_event.victim_id)
        if not killer or not victim:
            continue
        killer.gold += kill_event.gold_reward
        events.append(
            f"{killer.name} banks {kill_event.gold_reward} gold from {victim.name}'s bounty"
        )


def run_match_round(match: MatchState) -> list[str]:
    rng = random.Random(match.seed + match.round_number)
    players = match.active_players()
    rng.shuffle(players)
    events: list[str] = [f"Round {match.round_number}"]
    players_by_id = _players_by_id(match)

    if len(players) <= 1:
        return events

    paired: list[tuple[Player, Player]] = []
    bye_player: Player | None = None
    if len(players) % 2 == 1:
        bye_player = players.pop()
        events.append(f"{bye_player.name} gets a bye")

    for idx in range(0, len(players), 2):
        paired.append((players[idx], players[idx + 1]))

    for left, right in paired:
        result = run_duel(
            left.character,
            right.character,
            seed=match.seed + match.round_number * 997 + len(events),
        )
        if result.winner_id == left.character.char_id:
            winner, loser = left, right
        else:
            winner, loser = right, left

        kill_event = build_kill_event(
            killer_id=winner.player_id,
            victim_id=loser.player_id,
            killer_bounty=winner.bounty,
            victim_bounty=loser.bounty,
        )
        winner.bounty += kill_event.bounty_gain
        loser.bounty = apply_bounty_death_penalty(loser.bounty)
        _apply_kill_rewards(
            players_by_id=players_by_id,
            kill_events=[kill_event],
            events=events,
        )
        events.append(
            f"{winner.name} claims +{kill_event.bounty_gain} bounty from {loser.name}"
        )

        if player_has_infinite_health(loser):
            events.append(
                f"{winner.name} beat {loser.name} in {result.ticks} ticks; {loser.name} ignores the round damage"
            )
        else:
            loser.hp = max(0, loser.hp - ROUND_LOSS_DAMAGE)
            events.append(
                f"{winner.name} beat {loser.name} in {result.ticks} ticks; {loser.name} hp={loser.hp}"
            )
        if loser.hp == 0:
            loser.eliminated = True
            events.append(f"{loser.name} was eliminated")

    match.round_number += 1
    match.history.extend(events)
    return events


def get_winner(match: MatchState) -> Player | None:
    remaining = match.active_players()
    if len(remaining) == 1:
        return remaining[0]
    return None


def get_human_player(match: MatchState) -> Player | None:
    for player in match.players:
        if player.is_human:
            return player
    return None


def player_was_eliminated(match: MatchState) -> bool:
    human_player = get_human_player(match)
    return human_player is not None and human_player.eliminated


def is_match_over(match: MatchState) -> bool:
    return get_winner(match) is not None


def apply_arena_result(match: MatchState, arena: ArenaSimulation) -> list[str]:
    events = [f"Round {match.round_number} arena resolved"]
    winner_player_id = arena.winner_id
    players_by_id = _players_by_id(match)

    _apply_kill_rewards(
        players_by_id=players_by_id,
        kill_events=arena.kill_events,
        events=events,
    )
    for player_id, unit in arena.units.items():
        if player_id in players_by_id:
            players_by_id[player_id].bounty = unit.bounty

    for player in match.active_players():
        if player.player_id == winner_player_id:
            continue
        if player_has_infinite_health(player):
            events.append(f"{player.name} ignores the round damage")
            continue
        player.hp = max(0, player.hp - ROUND_LOSS_DAMAGE)
        events.append(f"{player.name} loses {ROUND_LOSS_DAMAGE} hp -> {player.hp}")
        if player.hp == 0:
            player.eliminated = True
            events.append(f"{player.name} was eliminated")
    match.round_number += 1
    match.history.extend(events)
    return events


def create_arena_for_round(
    match: MatchState,
    left: float,
    right: float,
    bottom: float,
    top: float,
) -> ArenaSimulation:
    return ArenaSimulation(
        players=match.active_players(),
        seed=match.seed + match.round_number * 1409,
        left=left,
        right=right,
        bottom=bottom,
        top=top,
    )
