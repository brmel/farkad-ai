"""The shape of a counted habit. Counting one needs the product's pillar specs, so it stays
in the backend; the sheet that reads one is shared."""

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
