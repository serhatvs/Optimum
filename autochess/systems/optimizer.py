from __future__ import annotations

import json
from pathlib import Path

try:
    from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum

    _GAMSPY_AVAILABLE = True
except Exception:
    Container = Set = Parameter = Variable = Equation = Model = Sum = None
    _GAMSPY_AVAILABLE = False

from autochess.models import Character, Item, ITEM_SLOTS


def _load_weights() -> dict[str, float]:
    balancing_path = Path(__file__).resolve().parents[2] / "data" / "balancing.json"
    with balancing_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)["weights"]


def _compute_item_score(
    item: Item,
    *,
    base_stats: dict[str, float],
    weights: dict[str, float],
) -> float:
    score = 0.0
    for mod in item.modifiers:
        if mod.stat not in weights:
            continue
        value = float(mod.value)
        if mod.mode == "percent":
            value = base_stats.get(mod.stat, 0.0) * value
        score += weights[mod.stat] * value
    return score


def _solve_greedy(
    item_scores: dict[str, float],
    offer_keys: list[str],
    key_to_item: dict[str, Item],
) -> dict[str, Item | None]:
    recommendation: dict[str, Item | None] = {slot: None for slot in ITEM_SLOTS}
    for slot in ITEM_SLOTS:
        candidates = [
            key
            for key in offer_keys
            if key_to_item[key].slot_type == slot and item_scores[key] > 0
        ]
        if not candidates:
            continue
        best_key = max(candidates, key=lambda key: item_scores[key])
        recommendation[slot] = key_to_item[best_key]
    return recommendation


def solve_survival_model(
    character: Character, available_items: list[Item]
) -> dict[str, Item | None]:
    if not available_items:
        return {slot: None for slot in ITEM_SLOTS}

    # 1. Load balancing weights.
    weights = _load_weights()

    # 2. Precompute score of each offered item using weighted modifier value.
    base_stats = {
        "max_hp": float(character.core_stats.max_hp),
        "atk": float(character.core_stats.atk),
        "def_stat": float(character.core_stats.def_stat),
        **character.base_aux_stats.as_dict(),
    }
    offer_keys = [f"{idx}:{item.item_id}" for idx, item in enumerate(available_items)]
    key_to_item = {
        f"{idx}:{item.item_id}": item for idx, item in enumerate(available_items)
    }
    item_scores = {
        key: _compute_item_score(key_to_item[key], base_stats=base_stats, weights=weights)
        for key in offer_keys
    }

    if not _GAMSPY_AVAILABLE:
        return _solve_greedy(item_scores, offer_keys, key_to_item)

    # 3. Setup GAMS model.
    m = Container()

    # 4. Define sets.
    slots = Set(m, name="slots", records=list(ITEM_SLOTS))
    offers = Set(m, name="offers", records=offer_keys)

    # 5. Define parameters and variables.
    item_score = Parameter(
        m,
        name="item_score",
        domain=offers,
        records=[(key, score) for key, score in item_scores.items()],
    )

    item_slot_map = Parameter(
        m,
        name="item_slot_map",
        domain=[offers, slots],
        records=[(key, key_to_item[key].slot_type, 1) for key in offer_keys],
    )

    x = Variable(m, name="x", domain=[offers, slots], type="binary")
    objective = Sum([offers, slots], x[offers, slots] * item_score[offers])

    # 6. Constraints.
    slot_limit = Equation(m, name="slot_limit", domain=slots)
    slot_limit[slots] = Sum(offers, x[offers, slots]) <= 1

    offer_uniqueness = Equation(m, name="offer_uniqueness", domain=offers)
    offer_uniqueness[offers] = Sum(slots, x[offers, slots]) <= 1

    slot_compatibility = Equation(m, name="slot_compatibility", domain=[offers, slots])
    slot_compatibility[offers, slots] = x[offers, slots] <= item_slot_map[offers, slots]

    # 7. Solve with GAMSPy and extract assignment from variable levels.
    model = Model(
        m,
        name="survival_model",
        equations=[slot_limit, offer_uniqueness, slot_compatibility],
        problem="MIP",
        sense="MAX",
        objective=objective,
    )

    recommendation: dict[str, Item | None] = {slot: None for slot in ITEM_SLOTS}
    try:
        model.solve()
        records = x.records
        if records is not None:
            for row in records.to_dict("records"):
                level = float(row.get("level", 0.0))
                if level < 0.5:
                    continue
                offer_key = str(row.get("offers", ""))
                slot = str(row.get("slots", ""))
                item = key_to_item.get(offer_key)
                if item is None or slot not in recommendation:
                    continue
                recommendation[slot] = item

        # If solver returned an empty/infeasible assignment, use deterministic fallback.
        if any(item is not None for item in recommendation.values()):
            return recommendation
    except Exception:
        pass

    return _solve_greedy(item_scores, offer_keys, key_to_item)
