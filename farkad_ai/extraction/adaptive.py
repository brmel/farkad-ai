from __future__ import annotations

import logging

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarConfigProtocol,
    PillarExtractionPort,
    TieredExtractionPort,
)
from farkad_ai.types import ModelTier, ModelUnavailableError, Unavailability

_log = logging.getLogger(__name__)


class AdaptiveExtractor[Config: PillarConfigProtocol](PillarExtractionPort[Config]):
    """Asks the fast tier first and the standard tier only when the fast answer did not parse."""

    def __init__(self, extractor: TieredExtractionPort[Config]) -> None:
        self._extractor = extractor

    async def extract(self, context: ExtractionContext[Config]) -> ExtractionResult:
        try:
            return await self._extractor.extract(context, tier=ModelTier.fast)
        except ModelUnavailableError as refusal:
            # A quota, a key or an outage refuses both tiers; only a schema escalates.
            if refusal.because is not Unavailability.output_did_not_parse:
                raise
            _log.info(
                "extraction_tier_escalated",
                extra={"pillar": context.config.pillar, "model": refusal.model},
            )
            return await self._extractor.extract(context, tier=ModelTier.standard)
