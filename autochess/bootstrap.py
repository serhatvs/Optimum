from __future__ import annotations

import random
from pathlib import Path

from autochess.models import MatchState, Player
from autochess.systems.generator import (
    assign_random_items,
    generate_character,
    parse_generator_config,
    parse_items,
)
from autochess.systems.loader import load_json
from autochess.systems.modifiers import recompute_aux_stats


def build_match(seed: int, data_dir: Path, player_name: str = "Player") -> MatchState:
    rng = random.Random(seed)
    archetypes_raw = load_json(data_dir / "archetypes.json")
    items_raw = load_json(data_dir / "items.json")
    generator_cfg = parse_generator_config(archetypes_raw)
    items = parse_items(items_raw["items"])

    players: list[Player] = []

    human_character = generate_character(
        rng=rng,
        config=generator_cfg,
        char_id="char_human_0",
        name=player_name,
        tier=2,
        star_level=1,
        forced_archetype="Hybrid",
    )
    assign_random_items(rng, human_character, items)
    recompute_aux_stats(human_character, generator_cfg.aux_caps)
    players.append(
        Player(
            player_id="player_human",
            name=player_name,
            is_human=True,
            character=human_character,
        )
    )

    archetype_names = [entry["name"] for entry in generator_cfg.archetypes]
    for i in range(1, 8):
        bot_character = generate_character(
            rng=rng,
            config=generator_cfg,
            char_id=f"char_bot_{i}",
            name=f"Bot-{i}",
            tier=rng.randint(1, 3),
            star_level=1,
            forced_archetype=rng.choice(archetype_names),
        )
        assign_random_items(rng, bot_character, items)
        recompute_aux_stats(bot_character, generator_cfg.aux_caps)
        players.append(
            Player(
                player_id=f"player_bot_{i}",
                name=f"Bot-{i}",
                is_human=False,
                character=bot_character,
            )
        )

    return MatchState(round_number=1, seed=seed, players=players)
