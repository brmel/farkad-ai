from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from statistics import median

from farkad_ai.memory.facts import folded

HABIT_WINDOW = timedelta(days=28)
TIMES_TO_BE_A_HABIT = 3
MAX_HABITS = 6

HOURS_A_DAY = 24


@dataclass(frozen=True, slots=True)
class UsualAmount:
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class HabitBaseline:
    pillar: str
    what: str | None
    times: int
    usual: UsualAmount | None
    usual_hour: int


@dataclass(frozen=True, slots=True)
class Occurrence:
    pillar: str
    what: str | None
    amount: UsualAmount | None
    hour: int


def baselines_from(occurrences: Iterable[Occurrence]) -> tuple[HabitBaseline, ...]:
    grouped: dict[tuple[str, str | None], list[Occurrence]] = {}
    for occurrence in occurrences:
        grouped.setdefault((occurrence.pillar, _named(occurrence.what)), []).append(occurrence)
    habits = [
        _habit(pillar, what, group)
        for (pillar, what), group in grouped.items()
        if len(group) >= TIMES_TO_BE_A_HABIT
    ]
    habits.sort(key=lambda habit: (-habit.times, habit.pillar, habit.what or ""))
    return tuple(habits[:MAX_HABITS])


def _named(what: str | None) -> str | None:
    if what is None or not what.strip():
        return None
    return folded(what)


def _habit(pillar: str, what: str | None, group: list[Occurrence]) -> HabitBaseline:
    return HabitBaseline(
        pillar=pillar,
        what=what,
        times=len(group),
        usual=_usual(entry.amount for entry in group),
        usual_hour=_usual_hour([entry.hour for entry in group]),
    )


def _usual_hour(hours: list[int]) -> int:
    return min(range(HOURS_A_DAY), key=lambda hour: (sum(_apart(hour, h) for h in hours), hour))


def _apart(one: int, other: int) -> int:
    gap = abs(one - other)
    return min(gap, HOURS_A_DAY - gap)


def _usual(amounts: Iterable[UsualAmount | None]) -> UsualAmount | None:
    known = [amount for amount in amounts if amount is not None]
    if not known or len({amount.unit for amount in known}) != 1:
        return None
    return UsualAmount(value=round(median(amount.value for amount in known), 1), unit=known[0].unit)
