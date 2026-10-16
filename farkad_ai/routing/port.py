from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import time
from enum import StrEnum
from typing import Protocol

from farkad_ai.models.port import Usage


class PillarSpec(Protocol):
    @property
    def pillar(self) -> str: ...

    @property
    def intent(self) -> str: ...


class PartOfDay(StrEnum):
    morning = "morning"
    midday = "midday"
    afternoon = "afternoon"
    evening = "evening"
    night = "night"


@dataclass(frozen=True, slots=True)
class StatedTime:
    phrase: str
    day_offset: int
    time_of_day: time | PartOfDay | None

    @property
    def names_a_day(self) -> bool:
        return self.day_offset != 0


class NothingToLogReason(StrEnum):
    not_a_health_log = "not_a_health_log"
    no_enabled_pillar = "no_enabled_pillar"


@dataclass(frozen=True, slots=True)
class Routed:
    transcript: str
    language: str
    states_a_lasting_fact: bool
    routes: frozenset[str]
    untracked: frozenset[str]
    mentions: Mapping[str, tuple[str, ...]]
    occurred_at_hints: Mapping[str, StatedTime | None]
    usage: Usage


@dataclass(frozen=True, slots=True)
class NothingToLog:
    transcript: str
    language: str
    states_a_lasting_fact: bool
    reason: NothingToLogReason
    usages: tuple[Usage, ...]


RoutingOutcome = Routed | NothingToLog
