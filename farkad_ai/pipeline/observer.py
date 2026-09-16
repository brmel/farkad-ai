from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from farkad_ai.pipeline.specialists import Attempt
    from farkad_ai.routing.router import RoutingOutcome


@dataclass(frozen=True, slots=True)
class RouteStarted:
    utterance: str
    has_media: bool


@dataclass(frozen=True, slots=True)
class RouteCompleted:
    outcome: RoutingOutcome


@dataclass(frozen=True, slots=True)
class ExtractionStarted:
    pillar: str


@dataclass(frozen=True, slots=True)
class ExtractionCompleted:
    pillar: str
    attempt: Attempt


type PipelineEvent = RouteStarted | RouteCompleted | ExtractionStarted | ExtractionCompleted


class PipelineObserver(Protocol):
    def on_event(self, event: PipelineEvent) -> None: ...


class NullObserver:
    def on_event(self, event: PipelineEvent) -> None:
        pass


@dataclass(slots=True)
class TraceObserver:
    events: list[PipelineEvent] = field(default_factory=list)

    def on_event(self, event: PipelineEvent) -> None:
        self.events.append(event)

    def routes(self) -> tuple[RouteCompleted, ...]:
        return tuple(e for e in self.events if isinstance(e, RouteCompleted))

    def extractions(self) -> tuple[ExtractionCompleted, ...]:
        return tuple(e for e in self.events if isinstance(e, ExtractionCompleted))
