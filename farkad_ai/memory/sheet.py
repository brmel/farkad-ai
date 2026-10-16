from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import timedelta
from enum import StrEnum

from farkad_ai.memory.facts import Fact
from farkad_ai.memory.habits import HabitBaseline

SHEET_CHARACTERS = 300
HEADING = "About this person:"


def core_sheet[Category: StrEnum](
    facts: Iterable[Fact[Category]],
    habits: Iterable[HabitBaseline],
    *,
    first_told: Sequence[Category],
    habit_window: timedelta,
) -> str:
    told = sorted(
        (fact for fact in facts if fact.enabled),
        key=lambda fact: (first_told.index(fact.disclosure.category), -fact.since.timestamp()),
    )
    lines = [f"- {fact.disclosure.content.strip()}" for fact in told]
    lines += [f"- {_described(habit, habit_window)}" for habit in habits]
    kept = [HEADING]
    for line in lines:
        if len("\n".join([*kept, line])) <= SHEET_CHARACTERS:
            kept.append(line)
    return "\n".join(kept) if len(kept) > 1 else ""


def _described(habit: HabitBaseline, window: timedelta) -> str:
    what = habit.pillar if habit.what is None else habit.what
    amount = "" if habit.usual is None else f" {habit.usual.value:g} {habit.usual.unit}"
    often = f"{habit.times}x in {window.days} days"
    return f"logs {what}{amount} around {habit.usual_hour:02d}:00 ({often})"
