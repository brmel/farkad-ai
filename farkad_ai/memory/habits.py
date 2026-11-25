from __future__ import annotations

from dataclasses import dataclass


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
