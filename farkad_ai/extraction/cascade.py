from __future__ import annotations

import logging

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    Extractor,
    TieredExtractor,
)
from farkad_ai.models.port import ModelTier, ModelUnavailableError, Unavailability

_log = logging.getLogger(__name__)


class CascadingExtractor(Extractor):
    def __init__(self, extractor: TieredExtractor) -> None:
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
