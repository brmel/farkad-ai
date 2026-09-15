from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from farkad_ai.extraction.port import PillarConfigProtocol
from farkad_ai.routing.pass_one import StatedTime
from farkad_ai.routing.router import NothingToLogReason
from farkad_ai.types import MediaBlob, Usage


class FailureReason(StrEnum):
    model_error = "model_error"
    unsupported_input = "unsupported_input"


class CaptureProfileProtocol(Protocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]: ...
    def config_for(self, pillar: str) -> PillarConfigProtocol: ...


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    profile: CaptureProfileProtocol
    text: str = ""
    media: tuple[MediaBlob, ...] = ()


@dataclass(frozen=True, slots=True)
class PillarEntries:
    pillar: str
    entries: tuple[dict[str, object], ...]
    stale_fields: frozenset[str]


@dataclass(frozen=True, slots=True)
class PillarRefused:
    pillar: str
    reason: FailureReason


@dataclass(frozen=True, slots=True)
class Logged:
    transcript: str
    language: str
    routes: frozenset[str]
    untracked: frozenset[str]
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


class CapturePipelinePort(Protocol):
    async def run(self, request: CaptureRequest) -> CaptureOutcome: ...
