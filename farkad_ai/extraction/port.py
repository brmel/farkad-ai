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
    mentions: tuple[str, ...]
    """The things in the transcript this pillar records, and nothing else in it."""
    media: tuple[MediaBlob, ...] = ()
    briefing: str = ""


@dataclass(frozen=True, slots=True)
class ExtractedEntry:
    """A finding belongs to the entry it was found in, never to that entry's siblings."""

    values: dict[str, object]
    findings: tuple[Finding, ...]

    @property
    def stale_fields(self) -> frozenset[str]:
        return frozenset(finding.field for finding in self.findings)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    pillar: str
    entries: tuple[ExtractedEntry, ...]
    usage: Usage
    confidence: float | None = None


class PillarExtractionPort[Config: PillarConfigProtocol](Protocol):
    async def extract(self, context: ExtractionContext[Config]) -> ExtractionResult: ...
