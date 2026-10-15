from __future__ import annotations

from farkad_ai.models.port import (
    Completion,
    MediaBlob,
    Model,
    ModelTier,
    PipelineStep,
    Prompt,
    Usage,
)
from farkad_ai.prompts import PromptAsset, briefed
from farkad_ai.routing.pass_one import INSTRUCTIONS, Mention, PassOne, routing_instructions
from farkad_ai.routing.port import (
    NotApplicable,
    NothingToLogReason,
    PillarRegistry,
    Routed,
    RoutingOutcome,
    StatedTime,
)


class Router:
    def __init__(
        self,
        model: Model,
        registry: PillarRegistry,
        *,
        instructions: PromptAsset = INSTRUCTIONS,
    ) -> None:
        self._model = model
        self._registry = registry
        self._asset = instructions
        self._instructions = routing_instructions(registry, instructions)

    async def route(
        self,
        tracked: frozenset[str],
        *,
        text: str = "",
        media: tuple[MediaBlob, ...] = (),
        briefing: str = "",
    ) -> RoutingOutcome:
        prompt = Prompt(
            step=PipelineStep.routing,
            instructions=briefed(self._instructions, briefing),
            instructions_version=self._asset.version,
            utterance=text,
            media=media,
        )
        completion: Completion[PassOne] = await self._model.complete(
            prompt, schema=PassOne, tier=ModelTier.fast
        )
        return self._decide(completion.value, tracked, completion.usage)

    def _decide(self, heard: PassOne, tracked: frozenset[str], usage: Usage) -> RoutingOutcome:
        if not heard.is_health_related:
            return NotApplicable(
                transcript=heard.transcript,
                language=heard.language,
                reason=NothingToLogReason.not_a_health_log,
                usage=usage,
            )

        known = [mention for mention in heard.mentions if self._registry.knows(mention.pillar)]
        named = frozenset(mention.pillar for mention in known)
        pillars = named & tracked
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
            occurred_at_hints={pillar: _first_stated(known, pillar) for pillar in sorted(pillars)},
            usage=usage,
        )


def _first_stated(mentions: list[Mention], pillar: str) -> StatedTime | None:
    hints = (mention.occurred_at_hint for mention in mentions if mention.pillar == pillar)
    return next((hint.stated() for hint in hints if hint is not None), None)
