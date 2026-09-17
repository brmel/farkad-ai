from __future__ import annotations

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
)
from farkad_ai.logging import get_logger

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
        except Exception as error:
            _log.info(
                "extraction_tier_escalated",
                extra={
                    "extra_fields": {
                        "pillar": context.config.pillar,
                        "reason": str(error),
                    }
                },
            )
            return await self._standard.extract(context)
