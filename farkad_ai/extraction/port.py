from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from farkad_ai.types import MediaBlob, ModelTier, Usage


@dataclass(frozen=True, slots=True)
class Finding:
    """Never rejects an entry; it lowers that field's confidence and asks for a look."""

    field: str
    reason: str


class TrackedPillar(Protocol):
    """A pillar as one user tracks it: everything extraction asks the consumer for."""

    @property
    def pillar(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def guidance(self) -> str: ...

    @property
    def examples(self) -> str:
        """Worked examples, already written in the units this user chose."""
        ...

    @property
    def entry_schema(self) -> type[BaseModel]: ...

    def review(self, entry: Mapping[str, object]) -> Iterable[Finding]: ...


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    pillar: TrackedPillar
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


class PillarExtractionPort(Protocol):
    async def extract(self, context: ExtractionContext) -> ExtractionResult: ...


class TieredExtractionPort(Protocol):
    async def extract(self, context: ExtractionContext, *, tier: ModelTier) -> ExtractionResult: ...
