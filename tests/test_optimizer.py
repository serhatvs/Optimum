import pytest
from autochess.models import Character, CoreStats, AuxStats, Item, Modifier
from autochess.systems.optimizer import solve_survival_model


def test_optimizer_recommendation():
    # Setup dummy character
    char = Character(
        char_id="c1",
        name="Test",
        archetype="test",
        tier=1,
        star_level=1,
        core_stats=CoreStats(max_hp=100, atk=10, def_stat=5),
        base_aux_stats=AuxStats(1.0, 100.0, 0.1, 1.0, 0.0),
        aux_stats=AuxStats(1.0, 100.0, 0.1, 1.0, 0.0),
    )

    # Setup dummy items
    item1 = Item(
        item_id="i1",
        name="HP Item",
        slot_type="body",
        rarity="common",
        modifiers=[Modifier("max_hp", "flat", 50, "test")],
    )
    item2 = Item(
        item_id="i2",
        name="Atk Item",
        slot_type="arms",
        rarity="common",
        modifiers=[Modifier("atk", "flat", 10, "test")],
    )

    available = [item1, item2]

    # Run solver
    recommendation = solve_survival_model(char, available)

    # Verify structure
    assert isinstance(recommendation, dict)
    # The solver logic itself is mocked out in the current optimizer.py
    # So we just verify it returns a valid slot mapping
