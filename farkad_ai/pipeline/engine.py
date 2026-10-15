from __future__ import annotations

import asyncio
import logging

from farkad_ai.extraction.cascade import CascadingExtractor
from farkad_ai.extraction.extractor import INSTRUCTIONS as EXTRACTION
from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
    TrackedPillar,
)
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline.port import (
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
from farkad_ai.routing.port import NotApplicable, PillarRegistryProtocol, Routed
from farkad_ai.routing.router import Router
from farkad_ai.types import ModelUnavailableError

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
        self._extractor = CascadingExtractor(PillarExtractor(model, instructions=extraction_prompt))

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
        contexts = [
            ExtractionContext(
                pillar=tracked[pillar],
                transcript=routed.transcript,
                mentions=said,
                media=request.media,
                briefing=request.briefing,
            )
            for pillar, said in sorted(routed.mentions.items())
        ]
        attempts = await asyncio.gather(
            *(_attempt(self._extractor, context) for context in contexts)
        )
        extracted: list[PillarEntries] = []
        refused: list[PillarRefused] = []
        usages = [routed.usage]
        for attempt in attempts:
            match attempt:
                case PillarRefused():
                    refused.append(attempt)
                case ExtractionResult(pillar=pillar, entries=entries, usage=usage):
                    usages.append(usage)
                    extracted.append(
                        PillarEntries(
                            pillar=pillar,
                            entries=entries,
                            occurred_at_hint=routed.occurred_at_hints[pillar],
                        )
                    )

        return Logged(
            transcript=routed.transcript,
            language=routed.language,
            routes=routed.pillars,
            untracked=routed.untracked,
            extracted=tuple(extracted),
            refused=tuple(refused),
            usages=tuple(usages),
        )


async def _attempt(
    extractor: PillarExtractionPort, context: ExtractionContext
) -> ExtractionResult | PillarRefused:
    try:
        return await extractor.extract(context)
    except ModelUnavailableError as unavailable:
        _log.warning(
            "pillar extraction failed",
            extra={
                "pillar": context.pillar.pillar,
                "model": unavailable.model,
                "because": unavailable.because.value,
            },
        )
        return PillarRefused(pillar=context.pillar.pillar, because=unavailable.because)
