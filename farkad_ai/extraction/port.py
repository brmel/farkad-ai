from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from farkad_ai.models.port import MediaBlob, ModelTier, Usage


@dataclass(frozen=True, slots=True)
class Finding:
    field: str
    reason: str


class TrackedPillar(Protocol):
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

    @property
    def label_fields(self) -> frozenset[str]:
        """Fields that only file an entry; an entry holding nothing else is dropped."""
        ...

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


class Extractor(Protocol):
    async def extract(self, context: ExtractionContext) -> ExtractionResult: ...


class TieredExtractor(Protocol):
    async def extract(self, context: ExtractionContext, *, tier: ModelTier) -> ExtractionResult: ...
