from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import time
from enum import StrEnum
from typing import Protocol

from farkad_ai.types import Usage


class PillarSpecProtocol(Protocol):
    @property
    def pillar(self) -> str: ...

    @property
    def intent(self) -> str: ...


class PillarRegistryProtocol(Protocol):
    def __iter__(self) -> Iterator[PillarSpecProtocol]: ...
    def knows(self, route: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class StatedTime:
    phrase: str
    day_offset: int
    clock: time | None

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
    pillars: frozenset[str]
    untracked: frozenset[str]
    mentions: Mapping[str, tuple[str, ...]]
    occurred_at_hints: Mapping[str, StatedTime | None]
    usage: Usage


@dataclass(frozen=True, slots=True)
class NotApplicable:
    transcript: str
    language: str
    reason: NothingToLogReason
    usage: Usage


RoutingOutcome = Routed | NotApplicable
