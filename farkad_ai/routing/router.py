from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from farkad_ai.models.port import (
    Completion,
    MediaBlob,
    Model,
    ModelTier,
    PipelineStep,
    Prompt,
    Usage,
)
from farkad_ai.prompts import briefed, version_of
from farkad_ai.routing.pass_one import (
    Mention,
    PassOne,
    TranscribedPassOne,
    routing_instructions,
)
from farkad_ai.routing.port import (
    NothingToLog,
    NothingToLogReason,
    PillarSpec,
    Routed,
    RoutingOutcome,
    StatedTime,
)


@dataclass(frozen=True, slots=True)
class _Pass:
    instructions: str
    schema: type[PassOne]

    @property
    def version(self) -> str:
        return version_of(self.instructions)


class Router:
    def __init__(
        self, model: Model, catalogue: Iterable[PillarSpec], *, rules: tuple[str, ...] = ()
    ) -> None:
        specs = tuple(catalogue)
        self._model = model
        self._known = frozenset(spec.pillar for spec in specs)
        self._typed = _Pass(routing_instructions(specs, rules=rules), PassOne)
        self._transcribing = _Pass(
            routing_instructions(specs, rules=rules, transcribing=True), TranscribedPassOne
        )

    async def route(
        self,
        tracked: frozenset[str],
        *,
        text: str = "",
        media: tuple[MediaBlob, ...] = (),
        briefing: str = "",
    ) -> RoutingOutcome:
        asking = self._transcribing if media else self._typed
        prompt = Prompt(
            step=PipelineStep.routing,
            instructions=briefed(asking.instructions, briefing),
            instructions_version=asking.version,
            utterance=text,
            media=media,
        )
        completion: Completion[PassOne] = await self._model.complete(
            prompt, schema=asking.schema, tier=ModelTier.fast
        )
        heard = completion.value
        return self._decide(heard, heard.transcript_of(text), tracked, completion.usage)

    def _decide(
        self, heard: PassOne, transcript: str, tracked: frozenset[str], usage: Usage
    ) -> RoutingOutcome:
        if not heard.is_health_related:
            return _nothing_to_log(heard, transcript, NothingToLogReason.not_a_health_log, usage)

        known = [mention for mention in heard.mentions if mention.pillar in self._known]
        named = frozenset(mention.pillar for mention in known)
        routes = named & tracked
        if not routes:
            return _nothing_to_log(heard, transcript, NothingToLogReason.no_enabled_pillar, usage)

        return Routed(
            transcript=transcript,
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


def _nothing_to_log(
    heard: PassOne, transcript: str, reason: NothingToLogReason, usage: Usage
) -> NothingToLog:
    return NothingToLog(
        transcript=transcript,
        language=heard.language,
        states_a_lasting_fact=heard.states_a_lasting_fact,
        reason=reason,
        usages=(usage,),
    )


def _first_stated(mentions: list[Mention], pillar: str) -> StatedTime | None:
    hints = (mention.occurred_at_hint for mention in mentions if mention.pillar == pillar)
    return next((hint.stated() for hint in hints if hint is not None), None)
