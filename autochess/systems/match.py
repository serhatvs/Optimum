from __future__ import annotations

import random

from autochess.models import MatchState, Player
from autochess.systems.combat import run_duel


ROUND_LOSS_DAMAGE = 12


def run_match_round(match: MatchState) -> list[str]:
    rng = random.Random(match.seed + match.round_number)
    players = match.active_players()
    rng.shuffle(players)
    events: list[str] = [f"Round {match.round_number}"]

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
