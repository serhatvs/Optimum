# AGENTS.md

## Introduction

This repository contains a pixel-art **FFA Auto-Chess** prototype built with `Arcade.py`.

The game is designed around deterministic, round-based auto-battles where:
- AI characters are generated randomly at match start from constrained archetype ranges.
- The player creates their own character and competes against generated opponents.
- Units battle automatically; strategy happens before combat via build and item decisions.

The architecture prioritizes data-driven balancing so stats, archetypes, and item behavior can be tuned through JSON files instead of constant code edits.

## Project Plan

### Gameplay Loop

1. Start match (human + bot roster).
2. Generate AI characters from archetypes and item pools.
3. Let player define their own character build.
4. Resolve pairings each round.
5. Run deterministic auto-battles.
6. Apply round damage/economy progression.
7. Continue until one player remains.

### Stat Model

- Core stats: `max_hp`, `atk`, `def`
- Auxiliary stats: `attack_speed`, `agility`, `crit_chance`, `mana_gain`, `lifesteal`
- Item slots: `weapon`, `armor`, `trinket_1`, `trinket_2`, `relic`

### Item/Modifier Rules

- Items are slot-bound and can apply both buffs and nerfs.
- Modifiers follow a shared format: `stat`, `mode`, `value`, `source`.
- Evaluation order:
  1. base values
  2. flat modifiers
  3. percent modifiers
  4. global stat clamps
- Unique effects should not stack with themselves.

### Architecture

- `autochess/models.py`: dataclasses for characters, modifiers, items, players
- `autochess/systems/generator.py`: constrained random generation
- `autochess/systems/modifiers.py`: buff/nerf application
- `autochess/systems/combat.py`: deterministic duel resolver
- `autochess/systems/match.py`: round flow and FFA elimination
- `autochess/views/`: basic Arcade UI views
- `data/`: `archetypes.json` and `items.json` for balancing

### Milestones

1. Core data models + loader
2. Random generation + player creation flow
3. Item buff/nerf pipeline with validation
4. Auto-battle simulation and FFA round manager
5. Arcade UI integration
6. Tests and balancing pass

### Immediate Implementation Priorities

1. Implement deterministic generation and combat with fixed seeds.
2. Keep item and archetype tuning externalized in JSON.
3. Add tests for stat recomputation, modifier stacking, and generation constraints.
