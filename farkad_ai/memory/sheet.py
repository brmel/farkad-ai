"""What every capture is told about its speaker, inside a budget small enough to be free."""

from __future__ import annotations

from collections.abc import Iterable

from farkad_ai.memory.facts import Fact, MemoryCategory
from farkad_ai.memory.habits import WINDOW, HabitBaseline

SHEET_CHARACTERS = 300
HEADING = "About this person:"
FIRST_TOLD = (
    MemoryCategory.medical,
    MemoryCategory.dietary,
    MemoryCategory.routine,
    MemoryCategory.preference,
    MemoryCategory.general,
)


def core_sheet(facts: Iterable[Fact], habits: Iterable[HabitBaseline]) -> str:
    """Constraints before habits, because a missed allergy costs more than a missed portion."""
    told = sorted(
        (fact for fact in facts if fact.enabled),
        key=lambda fact: (FIRST_TOLD.index(fact.disclosure.category), -fact.since.timestamp()),
    )
    lines = [f"- {fact.disclosure.content.strip()}" for fact in told]
    lines += [f"- {_described(habit)}" for habit in habits]
    kept = [HEADING]
    for line in lines:
        if len("\n".join([*kept, line])) <= SHEET_CHARACTERS:
            kept.append(line)
    return "\n".join(kept) if len(kept) > 1 else ""


def _described(habit: HabitBaseline) -> str:
    what = habit.pillar if habit.what is None else habit.what
    amount = "" if habit.usual is None else f" {habit.usual.value:g} {habit.usual.unit}"
    often = f"{habit.times}x in {WINDOW.days} days"
    return f"logs {what}{amount} around {habit.usual_hour:02d}:00 ({often})"
