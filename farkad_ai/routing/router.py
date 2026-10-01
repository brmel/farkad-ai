from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from farkad_ai.models.port import ModelPort
from farkad_ai.prompts import briefed
from farkad_ai.routing.pass_one import (
    INSTRUCTIONS,
    PassOne,
    PillarRegistryProtocol,
    StatedTime,
    routing_instructions,
)
from farkad_ai.types import Completion, MediaBlob, ModelTier, PipelineStep, Prompt, Usage


class NothingToLogReason(StrEnum):
    """Reason a capture logged nothing."""

    not_a_health_log = "not_a_health_log"
    no_enabled_pillar = "no_enabled_pillar"


@dataclass(frozen=True, slots=True)
class Routed:
    transcript: str
    language: str
    pillars: frozenset[str]
    untracked: frozenset[str]
    """What the intersection removed, so a partly untracked log still says so."""
    mentions: Mapping[str, tuple[str, ...]]
    """What each tracked pillar records, decided once so no two pillars record one thing."""
    occurred_at_hint: StatedTime | None
    usage: Usage


@dataclass(frozen=True, slots=True)
class NotApplicable:
    """No extraction call follows."""

    transcript: str
    language: str
    reason: NothingToLogReason
    usage: Usage


RoutingOutcome = Routed | NotApplicable


class TrackingProfileProtocol(Protocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]: ...


class Router:
    def __init__(self, model: ModelPort, registry: PillarRegistryProtocol) -> None:
        self._model = model
        self._registry = registry
        self._instructions = routing_instructions(registry)

    async def route(
        self,
        profile: TrackingProfileProtocol,
        *,
        text: str = "",
        media: tuple[MediaBlob, ...] = (),
        briefing: str = "",
    ) -> RoutingOutcome:
        prompt = Prompt(
            step=PipelineStep.routing,
            instructions=briefed(self._instructions, briefing),
            instructions_version=INSTRUCTIONS.version,
            utterance=text,
            media=media,
        )
        completion: Completion[PassOne] = await self._model.complete(
            prompt, schema=PassOne, tier=ModelTier.fast
        )
        return self.decide(completion.value, profile, completion.usage)

    def decide(
        self, heard: PassOne, profile: TrackingProfileProtocol, usage: Usage
    ) -> RoutingOutcome:
        if not heard.is_health_related:
            return NotApplicable(
                transcript=heard.transcript,
                language=heard.language,
                reason=NothingToLogReason.not_a_health_log,
                usage=usage,
            )

        known = [mention for mention in heard.mentions if self._registry.knows(mention.pillar)]
        named = frozenset(mention.pillar for mention in known)
        pillars = profile.restrict(named)
        if not pillars:
            return NotApplicable(
                transcript=heard.transcript,
                language=heard.language,
                reason=NothingToLogReason.no_enabled_pillar,
                usage=usage,
            )

        return Routed(
            transcript=heard.transcript,
            language=heard.language,
            pillars=pillars,
            untracked=named - pillars,
            mentions={
                pillar: tuple(mention.said for mention in known if mention.pillar == pillar)
                for pillar in sorted(pillars)
            },
            occurred_at_hint=heard.occurred_at_hint.stated() if heard.occurred_at_hint else None,
            usage=usage,
        )
