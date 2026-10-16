from __future__ import annotations

from collections.abc import Iterable

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
    NothingToLog,
    NothingToLogReason,
    PillarSpec,
    Routed,
    RoutingOutcome,
    StatedTime,
)


class Router:
    def __init__(
        self,
        model: Model,
        catalogue: Iterable[PillarSpec],
        *,
        instructions: PromptAsset = INSTRUCTIONS,
    ) -> None:
        specs = tuple(catalogue)
        self._model = model
        self._known = frozenset(spec.pillar for spec in specs)
        self._asset = instructions
        self._instructions = routing_instructions(specs, instructions)

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
            return NothingToLog(
                transcript=heard.transcript,
                language=heard.language,
                states_a_lasting_fact=heard.states_a_lasting_fact,
                reason=NothingToLogReason.not_a_health_log,
                usages=(usage,),
            )

        known = [mention for mention in heard.mentions if mention.pillar in self._known]
        named = frozenset(mention.pillar for mention in known)
        routes = named & tracked
        if not routes:
            return NothingToLog(
                transcript=heard.transcript,
                language=heard.language,
                states_a_lasting_fact=heard.states_a_lasting_fact,
                reason=NothingToLogReason.no_enabled_pillar,
                usages=(usage,),
            )

        return Routed(
            transcript=heard.transcript,
            language=heard.language,
            states_a_lasting_fact=heard.states_a_lasting_fact,
            routes=routes,
            untracked=named - routes,
            mentions={
                pillar: tuple(mention.said for mention in known if mention.pillar == pillar)
                for pillar in sorted(routes)
            },
            occurred_at_hints={pillar: _first_stated(known, pillar) for pillar in sorted(routes)},
            usage=usage,
        )


def _first_stated(mentions: list[Mention], pillar: str) -> StatedTime | None:
    hints = (mention.occurred_at_hint for mention in mentions if mention.pillar == pillar)
    return next((hint.stated() for hint in hints if hint is not None), None)
