from __future__ import annotations

from autochess.models import KillEvent


BOUNTY_GOLD_BASE = 10
BOUNTY_GOLD_MULTIPLIER = 10


def calculate_bounty_gain(killer_bounty: int, victim_bounty: int) -> int:
    return max(1, 1 + ((victim_bounty - killer_bounty) // 2))


def calculate_bounty_gold(victim_bounty: int) -> int:
    return BOUNTY_GOLD_BASE + (victim_bounty * BOUNTY_GOLD_MULTIPLIER)


def apply_bounty_death_penalty(current_bounty: int) -> int:
    return current_bounty // 2


def build_kill_event(
    *,
    killer_id: str,
    victim_id: str,
    killer_bounty: int,
    victim_bounty: int,
) -> KillEvent:
    return KillEvent(
        killer_id=killer_id,
        victim_id=victim_id,
        victim_bounty_at_kill=victim_bounty,
        gold_reward=calculate_bounty_gold(victim_bounty),
        bounty_gain=calculate_bounty_gain(killer_bounty, victim_bounty),
    )
