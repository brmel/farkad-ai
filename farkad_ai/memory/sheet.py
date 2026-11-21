from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from farkad_ai.memory.facts import Fact
from farkad_ai.memory.habits import HABIT_WINDOW, HabitBaseline
from farkad_ai.prompts import prompt

_SHEET = prompt("about_this_person")
_HABIT = prompt("usual_habit")


def core_sheet[Category: StrEnum](
    facts: Iterable[Fact[Category]],
    habits: Iterable[HabitBaseline],
    *,
    first_told: Sequence[Category],
) -> str:
    told = sorted(
        (fact for fact in facts if fact.enabled),
        key=lambda fact: (first_told.index(fact.disclosure.category), -fact.since.timestamp()),
    )
    lines = [f"- {_one_line(fact.disclosure.content)}" for fact in told]
    lines += [f"- {_described(habit)}" for habit in habits]
    return _SHEET.format(lines="\n".join(lines)) if lines else ""


def _one_line(said: str) -> str:
    return " ".join(said.split())


def _described(habit: HabitBaseline) -> str:
    what = habit.pillar if habit.what is None else habit.what
    amount = "" if habit.usual is None else f" {habit.usual.value:g} {habit.usual.unit}"
    return _HABIT.format(
        what=what,
        amount=amount,
        hour=habit.usual_hour,
        times=habit.times,
        days=HABIT_WINDOW.days,
    )
