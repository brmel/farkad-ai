from __future__ import annotations

import logging

from farkad_ai.extraction.port import PillarConfigProtocol, PillarExtractionPort
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline.observer import (
    ExtractionCompleted,
    ExtractionStarted,
    NullObserver,
    PipelineObserver,
    RouteCompleted,
    RouteStarted,
)
from farkad_ai.pipeline.specialists import Extracted, Failed, extract_each
from farkad_ai.pipeline.types import (
    CaptureOutcome,
    CapturePipelinePort,
    CaptureRequest,
    Logged,
    NothingToLog,
    PillarEntries,
    PillarRefused,
)
from farkad_ai.routing.pass_one import PillarRegistryProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router

_log = logging.getLogger(__name__)


def build_pipeline[Config: PillarConfigProtocol](
    model: ModelPort,
    registry: PillarRegistryProtocol,
    extractor: PillarExtractionPort[Config],
    *,
    observer: PipelineObserver | None = None,
) -> TwoPassPipeline[Config]:
    return TwoPassPipeline(Router(model, registry), extractor, observer=observer)


class TwoPassPipeline[Config: PillarConfigProtocol](CapturePipelinePort[Config]):
    def __init__(
        self,
        router: Router,
        extractor: PillarExtractionPort[Config],
        *,
        observer: PipelineObserver | None = None,
    ) -> None:
        self._router = router
        self._extractor = extractor
        self._observer = observer if observer is not None else NullObserver()

    async def run(self, request: CaptureRequest[Config]) -> CaptureOutcome:
        self._observer.on_event(RouteStarted(utterance=request.text, has_media=bool(request.media)))
        routed = await self._router.route(
            request.profile,
            text=request.text,
            media=request.media,
            briefing=request.briefing,
        )
        self._observer.on_event(RouteCompleted(outcome=routed))
        match routed:
            case NotApplicable():
                _log.info("nothing to log in this capture", extra={"reason": routed.reason})
                return NothingToLog(
                    transcript=routed.transcript,
                    language=routed.language,
                    reason=routed.reason,
                    usages=(routed.usage,),
                )
            case Routed():
                _log.info("routed", extra={"pillars": sorted(routed.pillars)})
                return await self._extract(routed, request)

    async def _extract(self, routed: Routed, request: CaptureRequest[Config]) -> Logged:
        for pillar in sorted(routed.pillars):
            self._observer.on_event(ExtractionStarted(pillar=pillar))
        attempts = await extract_each(
            self._extractor,
            routed.mentions,
            routed.transcript,
            request.profile,
            media=request.media,
            briefing=request.briefing,
        )
        extracted: list[PillarEntries] = []
        refused: list[PillarRefused] = []
        usages = [routed.usage]
        for attempt in attempts:
            self._observer.on_event(ExtractionCompleted(pillar=attempt.pillar, attempt=attempt))
            match attempt:
                case Failed(pillar=pillar, reason=reason):
                    refused.append(PillarRefused(pillar=pillar, reason=reason))
                case Extracted(pillar=pillar, result=result):
                    usages.append(result.usage)
                    extracted.append(
                        PillarEntries(
                            pillar=pillar,
                            entries=result.entries,
                            stale_fields=frozenset(finding.field for finding in result.findings),
                        )
                    )

        return Logged(
            transcript=routed.transcript,
            language=routed.language,
            routes=routed.pillars,
            untracked=routed.untracked,
            occurred_at_hint=routed.occurred_at_hint,
            extracted=tuple(extracted),
            refused=tuple(refused),
            usages=tuple(usages),
        )
