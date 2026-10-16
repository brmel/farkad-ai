from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from farkad_ai.extraction.port import ExtractedEntry, TrackedPillar
from farkad_ai.models.port import MediaBlob, Unavailability, Usage
from farkad_ai.routing.port import NothingToLog, StatedTime


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    tracked: tuple[TrackedPillar, ...]
    text: str = ""
    media: tuple[MediaBlob, ...] = ()
    briefing: str = ""


@dataclass(frozen=True, slots=True)
class PillarEntries:
    pillar: str
    entries: tuple[ExtractedEntry, ...]
    occurred_at_hint: StatedTime | None


@dataclass(frozen=True, slots=True)
class PillarRefused:
    pillar: str
    because: Unavailability


@dataclass(frozen=True, slots=True)
class Logged:
    transcript: str
    language: str
    states_a_lasting_fact: bool
    routes: frozenset[str]
    untracked: frozenset[str]
    extracted: tuple[PillarEntries, ...]
    refused: tuple[PillarRefused, ...]
    usages: tuple[Usage, ...]


CaptureOutcome = Logged | NothingToLog


class CaptureEngine(Protocol):
    async def capture(self, request: CaptureRequest) -> CaptureOutcome: ...
