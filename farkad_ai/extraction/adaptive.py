from __future__ import annotations

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
)
from farkad_ai.logging import get_logger
from farkad_ai.types import ModelUnavailableError, Unavailability

_log = get_logger(__name__)


class AdaptiveExtractor(PillarExtractionPort):
    def __init__(
        self,
        fast: PillarExtractionPort,
        standard: PillarExtractionPort,
    ) -> None:
        self._fast = fast
        self._standard = standard

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        try:
            return await self._fast.extract(context)
        except ModelUnavailableError as refusal:
            # A quota, a key or an outage refuses both tiers; only a schema escalates.
            if refusal.because is not Unavailability.output_did_not_parse:
                raise
            _log.info(
                "extraction_tier_escalated",
                extra={
                    "extra_fields": {
                        "pillar": context.config.pillar,
                        "model": refusal.model,
                    }
                },
            )
            return await self._standard.extract(context)
