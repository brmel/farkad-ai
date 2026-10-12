from __future__ import annotations

import logging

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
    TieredExtractionPort,
)
from farkad_ai.types import ModelTier, ModelUnavailableError, Unavailability

_log = logging.getLogger(__name__)


class AdaptiveExtractor(PillarExtractionPort):
    def __init__(self, extractor: TieredExtractionPort) -> None:
        self._extractor = extractor

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        try:
            return await self._extractor.extract(context, tier=ModelTier.fast)
        except ModelUnavailableError as refusal:
            if refusal.because is not Unavailability.output_did_not_parse:
                raise
            _log.info(
                "extraction_tier_escalated",
                extra={"pillar": context.pillar.pillar, "model": refusal.model},
            )
            return await self._extractor.extract(context, tier=ModelTier.standard)
