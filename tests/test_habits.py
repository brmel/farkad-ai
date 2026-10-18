from __future__ import annotations

import pytest

from farkad_ai.memory.habits import (
    MAX_HABITS,
    TIMES_TO_BE_A_HABIT,
    HabitBaseline,
    Logged,
    UsualAmount,
    baselines_from,
)


def ibuprofen(dose: float, unit: str = "mg") -> Logged:
    return Logged(pillar="drugs", what="ibuprofen", amount=UsualAmount(dose, unit), hour=8)


def tea(hour: int = 8, what: str | None = "tea") -> Logged:
    return Logged(pillar="water", what=what, amount=None, hour=hour)


def test_a_usual_amount_is_the_median_of_those_logged() -> None:
    habits = baselines_from([ibuprofen(81), ibuprofen(300), ibuprofen(350), ibuprofen(400)])

    assert habits == (
        HabitBaseline(
            pillar="drugs",
            what="ibuprofen",
            times=4,
            usual=UsualAmount(value=325.0, unit="mg"),
            usual_hour=8,
        ),
    )


def test_amounts_logged_in_different_units_have_no_usual_amount() -> None:
    (habit,) = baselines_from([ibuprofen(400), ibuprofen(400), ibuprofen(0.4, "g")])

    assert habit.usual is None


def test_fewer_than_enough_times_is_not_a_habit() -> None:
    assert baselines_from([tea()] * (TIMES_TO_BE_A_HABIT - 1)) == ()


def test_only_the_most_logged_habits_are_kept() -> None:
    many = [
        Logged(pillar="food", what=f"dish {n}", amount=None, hour=12)
        for n in range(MAX_HABITS + 2)
        for _ in range(TIMES_TO_BE_A_HABIT + n)
    ]

    kept = baselines_from(many)

    assert len(kept) == MAX_HABITS
    assert kept[0].what == f"dish {MAX_HABITS + 1}"


def test_a_habit_either_side_of_midnight_is_kept_near_midnight() -> None:
    (habit,) = baselines_from([tea(23), tea(23), tea(0), tea(0)])

    assert habit.usual_hour in {23, 0}


@pytest.mark.parametrize(
    ("written", "named"),
    [(("Green  Tea ", "green tea", "GREEN TEA"), "green tea"), (("  ", None, ""), None)],
)
def test_names_differing_only_in_case_or_spacing_are_one_habit(
    written: tuple[str | None, ...], named: str | None
) -> None:
    (habit,) = baselines_from(tea(what=what) for what in written)

    assert (habit.what, habit.times) == (named, len(written))
