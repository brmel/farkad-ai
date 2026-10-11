"""The shape of a counted habit; the consumer does the counting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

WINDOW = timedelta(days=28)


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
