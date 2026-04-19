from autochess.models import ITEM_SLOTS
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
    assert set(recommendation.keys()) == set(ITEM_SLOTS)

    # Verify optimizer gives a substantial answer for offered slot-compatible items.
    assert recommendation["body"] is item1
    assert recommendation["arms"] is item2


def test_optimizer_skips_negative_value_item() -> None:
    char = Character(
        char_id="c2",
        name="Negative Test",
        archetype="test",
        tier=1,
        star_level=1,
        core_stats=CoreStats(max_hp=100, atk=10, def_stat=5),
        base_aux_stats=AuxStats(1.0, 100.0, 0.1, 1.0, 0.0),
        aux_stats=AuxStats(1.0, 100.0, 0.1, 1.0, 0.0),
    )

    bad_arms = Item(
        item_id="i_bad",
        name="Cursed Arms",
        slot_type="arms",
        rarity="common",
        modifiers=[Modifier("atk", "flat", -500, "test")],
    )

    recommendation = solve_survival_model(char, [bad_arms])

    assert recommendation["arms"] is None
