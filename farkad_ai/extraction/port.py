from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from farkad_ai.types import MediaBlob, Usage


@dataclass(frozen=True, slots=True)
class Finding:
    """Never rejects an entry; it lowers that field's confidence and asks for a look."""

    field: str
    reason: str


class PillarConfigProtocol(Protocol):
    @property
    def pillar(self) -> str: ...


@dataclass(frozen=True, slots=True)
class ExtractionContext[Config: PillarConfigProtocol]:
    config: Config
    transcript: str
    media: tuple[MediaBlob, ...] = ()
    briefing: str = ""


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    pillar: str
    entries: tuple[dict[str, object], ...]
    findings: tuple[Finding, ...]
    usage: Usage
    confidence: float | None = None


class PillarExtractionPort[Config: PillarConfigProtocol](Protocol):
    async def extract(self, context: ExtractionContext[Config]) -> ExtractionResult: ...
