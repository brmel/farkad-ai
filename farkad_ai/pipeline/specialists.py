from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
    TrackedPillar,
)
from farkad_ai.pipeline.types import PillarRefused
from farkad_ai.types import MediaBlob, ModelUnavailableError

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Extracted:
    pillar: str
    result: ExtractionResult


Attempt = Extracted | PillarRefused


async def extract_each(
    extractor: PillarExtractionPort,
    mentions: Mapping[str, tuple[str, ...]],
    transcript: str,
    tracked: Mapping[str, TrackedPillar],
    media: tuple[MediaBlob, ...] = (),
    briefing: str = "",
) -> list[Attempt]:
    return list(
        await asyncio.gather(
            *(
                _attempt(
                    extractor,
                    tracked[pillar],
                    mentions[pillar],
                    transcript,
                    media=media,
                    briefing=briefing,
                )
                for pillar in sorted(mentions)
            )
        )
    )


async def _attempt(
    extractor: PillarExtractionPort,
    pillar: TrackedPillar,
    said: tuple[str, ...],
    transcript: str,
    *,
    media: tuple[MediaBlob, ...],
    briefing: str,
) -> Attempt:
    context = ExtractionContext(
        pillar=pillar,
        transcript=transcript,
        mentions=said,
        media=media,
        briefing=briefing,
    )
    try:
        return Extracted(pillar=pillar.pillar, result=await extractor.extract(context))
    except ModelUnavailableError as unavailable:
        _log.warning(
            "pillar extraction failed",
            extra={
                "pillar": pillar.pillar,
                "model": unavailable.model,
                "because": unavailable.because.value,
            },
        )
        return PillarRefused(pillar=pillar.pillar, because=unavailable.because)
