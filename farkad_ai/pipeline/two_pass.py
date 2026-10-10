from __future__ import annotations

import logging

from farkad_ai.extraction.port import PillarConfigProtocol, PillarExtractionPort
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
from farkad_ai.routing.router import NotApplicable, Routed, Router

_log = logging.getLogger(__name__)


class TwoPassPipeline[Config: PillarConfigProtocol](CapturePipelinePort[Config]):
    def __init__(
        self,
        router: Router,
        extractor: PillarExtractionPort[Config],
    ) -> None:
        self._router = router
        self._extractor = extractor

    async def run(self, request: CaptureRequest[Config]) -> CaptureOutcome:
        routed = await self._router.route(
            request.profile,
            text=request.text,
            media=request.media,
            briefing=request.briefing,
        )
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
            match attempt:
                case Failed(pillar=pillar, because=because):
                    refused.append(PillarRefused(pillar=pillar, because=because))
                case Extracted(pillar=pillar, result=result):
                    usages.append(result.usage)
                    extracted.append(PillarEntries(pillar=pillar, entries=result.entries))

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
