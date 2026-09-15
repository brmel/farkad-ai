from __future__ import annotations

from farkad_ai.extraction.port import PillarExtractionPort
from farkad_ai.models.port import ModelPort
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


def build_pipeline(
    model: ModelPort,
    registry: PillarRegistryProtocol,
    extractor: PillarExtractionPort,
) -> TwoPassPipeline:
    return TwoPassPipeline(Router(model, registry), extractor)


class TwoPassPipeline(CapturePipelinePort):
    def __init__(self, router: Router, extractor: PillarExtractionPort) -> None:
        self._router = router
        self._extractor = extractor

    async def run(self, request: CaptureRequest) -> CaptureOutcome:
        routed = await self._router.route(request.profile, text=request.text, media=request.media)
        match routed:
            case NotApplicable():
                return NothingToLog(
                    transcript=routed.transcript,
                    language=routed.language,
                    reason=routed.reason,
                    usages=(routed.usage,),
                )
            case Routed():
                return await self._extract(routed, request)

    async def _extract(self, routed: Routed, request: CaptureRequest) -> Logged:
        attempts = await extract_each(
            self._extractor,
            sorted(routed.pillars),
            routed.transcript,
            request.profile,
            media=request.media,
        )
        extracted: list[PillarEntries] = []
        refused: list[PillarRefused] = []
        usages = [routed.usage]
        for attempt in attempts:
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
