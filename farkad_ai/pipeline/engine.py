from __future__ import annotations

import logging

from farkad_ai.extraction.adaptive import AdaptiveExtractor
from farkad_ai.extraction.extractor import INSTRUCTIONS as EXTRACTION
from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import TrackedPillar
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline.specialists import Extracted, Failed, extract_each
from farkad_ai.pipeline.types import (
    CaptureEnginePort,
    CaptureOutcome,
    CaptureRequest,
    Logged,
    NothingToLog,
    PillarEntries,
    PillarRefused,
)
from farkad_ai.prompts import PromptAsset
from farkad_ai.routing.pass_one import INSTRUCTIONS as ROUTING
from farkad_ai.routing.pass_one import PillarRegistryProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router

_log = logging.getLogger(__name__)


class CaptureEngine(CaptureEnginePort):
    """Routes a capture once, then extracts each tracked pillar it names, side by side."""

    def __init__(
        self,
        model: ModelPort,
        catalogue: PillarRegistryProtocol,
        *,
        routing_prompt: PromptAsset = ROUTING,
        extraction_prompt: PromptAsset = EXTRACTION,
    ) -> None:
        self._router = Router(model, catalogue, instructions=routing_prompt)
        self._extractor = AdaptiveExtractor(PillarExtractor(model, instructions=extraction_prompt))

    async def capture(self, request: CaptureRequest) -> CaptureOutcome:
        tracked = {pillar.pillar: pillar for pillar in request.tracked}
        routed = await self._router.route(
            frozenset(tracked),
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
                return await self._extract(routed, request, tracked)

    async def _extract(
        self, routed: Routed, request: CaptureRequest, tracked: dict[str, TrackedPillar]
    ) -> Logged:
        attempts = await extract_each(
            self._extractor,
            routed.mentions,
            routed.transcript,
            tracked,
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
