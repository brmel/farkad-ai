from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from farkad_ai.extraction.port import ExtractedEntry, PillarConfigProtocol
from farkad_ai.routing.pass_one import StatedTime
from farkad_ai.routing.router import NothingToLogReason
from farkad_ai.types import MediaBlob, Unavailability, Usage


class CaptureProfileProtocol[Config: PillarConfigProtocol](Protocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]: ...
    def config_for(self, pillar: str) -> Config: ...


@dataclass(frozen=True, slots=True)
class CaptureRequest[Config: PillarConfigProtocol]:
    profile: CaptureProfileProtocol[Config]
    text: str = ""
    media: tuple[MediaBlob, ...] = ()
    briefing: str = ""


@dataclass(frozen=True, slots=True)
class PillarEntries:
    pillar: str
    entries: tuple[ExtractedEntry, ...]


@dataclass(frozen=True, slots=True)
class PillarRefused:
    """Reported beside the pillars that did come back, never instead of them."""

    pillar: str
    because: Unavailability


@dataclass(frozen=True, slots=True)
class Logged:
    transcript: str
    language: str
    routes: frozenset[str]
    untracked: frozenset[str]
    """Spoken about and not tracked, which a capture must say rather than drop."""
    occurred_at_hint: StatedTime | None
    extracted: tuple[PillarEntries, ...]
    refused: tuple[PillarRefused, ...]
    usages: tuple[Usage, ...]


@dataclass(frozen=True, slots=True)
class NothingToLog:
    transcript: str
    language: str
    reason: NothingToLogReason
    usages: tuple[Usage, ...]


CaptureOutcome = Logged | NothingToLog


class CapturePipelinePort[Config: PillarConfigProtocol](Protocol):
    async def run(self, request: CaptureRequest[Config]) -> CaptureOutcome: ...
