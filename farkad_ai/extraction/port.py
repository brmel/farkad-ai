from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from farkad_ai.types import MediaBlob, Usage


@dataclass(frozen=True, slots=True)
class Finding:
    field: str
    reason: str


class PillarConfigProtocol(Protocol):
    @property
    def pillar(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    config: PillarConfigProtocol
    transcript: str
    media: tuple[MediaBlob, ...] = ()
    memory_context: str = ""


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    pillar: str
    entries: tuple[dict[str, object], ...]
    findings: tuple[Finding, ...]
    usage: Usage
    confidence: float | None = None


class PillarExtractionPort(Protocol):
    async def extract(self, context: ExtractionContext) -> ExtractionResult: ...
