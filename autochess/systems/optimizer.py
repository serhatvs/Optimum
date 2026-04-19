from __future__ import annotations
import json
from gamspy import Container, Set, Parameter, Variable, Equation, Model, Sum
from autochess.models import Character, Item, ITEM_SLOTS, AUX_STATS


def solve_survival_model(
    character: Character, available_items: list[Item]
) -> dict[str, Item | None]:
    # 1. Load weights
    with open("data/balancing.json", "r") as f:
        weights = json.load(f)["weights"]

    # 2. Setup GAMS Container
    m = Container()

    # 3. Define Sets
    slots = Set(m, name="slots", records=list(ITEM_SLOTS))
    items = Set(m, name="items", records=[i.item_id for i in available_items])
    attributes = Set(
        m, name="attributes", records=list(AUX_STATS) + ["max_hp", "atk", "def_stat"]
    )

    # 4. Define Parameters
    # Character Base Stats
    base_stats = {
        "max_hp": float(character.core_stats.max_hp),
        "atk": float(character.core_stats.atk),
        "def_stat": float(character.core_stats.def_stat),
        **character.base_aux_stats.as_dict(),
    }
    char_stats_p = Parameter(
        m,
        name="char_stats",
        domain=attributes,
        records=[(k, v) for k, v in base_stats.items()],
    )

    # Weights
    weights_p = Parameter(
        m,
        name="weights",
        domain=attributes,
        records=[(k, v) for k, v in weights.items()],
    )

    # Item Bonuses (simplified: only flat or percent, based on base stats)
    # In a full impl, we'd handle complex modifier logic here
    item_bonus_data = []
    for item in available_items:
        for mod in item.modifiers:
            val = mod.value
            if mod.mode == "percent":
                val = base_stats.get(mod.stat, 0.0) * mod.value
            item_bonus_data.append((item.item_id, mod.stat, val))

    item_bonus_p = Parameter(
        m, name="item_bonus", domain=[items, attributes], records=item_bonus_data
    )

    # 5. Define Variables
    x = Variable(m, name="x", domain=[items, slots], type="binary")

    # 6. Define Objective
    # Maximize S = sum(a in A, weight(a) * (base(a) + sum(i, s, x(i,s) * bonus(i,a))))
    # This simplifies to: Maximize sum(i, s, x(i,s) * sum(a, weight(a) * bonus(i,a)))

    # Calculate item efficiency score: sum(a, weight(a) * bonus(i,a))
    item_efficiency = Sum(
        attributes, weights_p[attributes] * item_bonus_p[items, attributes]
    )

    objective = Sum([items, slots], x[items, slots] * item_efficiency[items])

    # 7. Define Constraints
    slot_limit = Equation(m, name="slot_limit", domain=slots)
    slot_limit[slots] = Sum(items, x[items, slots]) <= 1

    item_uniqueness = Equation(m, name="item_uniqueness", domain=items)
    item_uniqueness[items] = Sum(slots, x[items, slots]) <= 1

    # Also restrict item to its slot_type
    # This requires a parameter mapping item to slot type
    item_slot_map = Parameter(
        m,
        name="item_slot_map",
        domain=[items, slots],
        records=[(i.item_id, i.slot_type, 1) for i in available_items],
    )

    slot_compatibility = Equation(m, name="slot_compatibility", domain=[items, slots])
    slot_compatibility[items, slots] = x[items, slots] <= item_slot_map[items, slots]

    # 8. Solve
    model = Model(
        m,
        name="survival_model",
        equations=[slot_limit, item_uniqueness, slot_compatibility],
        problem="MIP",
        sense="MAX",
        objective=objective,
    )

    # NOTE: GAMS solver selection might be needed depending on license
    # model.solve(solver="CBC")

    # Placeholder: assume successful solve and extract x.records
    # For now, return empty or dummy for testing
    return {slot: None for slot in ITEM_SLOTS}
