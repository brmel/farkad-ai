from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarConfigProtocol,
    PillarExtractionPort,
)
from farkad_ai.pipeline.types import CaptureProfileProtocol, FailureReason
from farkad_ai.types import MediaBlob, ModelUnavailableError

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Extracted:
    pillar: str
    result: ExtractionResult


@dataclass(frozen=True, slots=True)
class Failed:
    pillar: str
    reason: FailureReason


Attempt = Extracted | Failed


async def extract_each[Config: PillarConfigProtocol](
    engine: PillarExtractionPort[Config],
    mentions: Mapping[str, tuple[str, ...]],
    transcript: str,
    profile: CaptureProfileProtocol[Config],
    media: tuple[MediaBlob, ...] = (),
    briefing: str = "",
) -> list[Attempt]:
    return list(
        await asyncio.gather(
            *(
                _attempt(
                    engine,
                    pillar,
                    mentions[pillar],
                    transcript,
                    profile,
                    media=media,
                    briefing=briefing,
                )
                for pillar in sorted(mentions)
            )
        )
    )


async def _attempt[Config: PillarConfigProtocol](
    engine: PillarExtractionPort[Config],
    pillar: str,
    said: tuple[str, ...],
    transcript: str,
    profile: CaptureProfileProtocol[Config],
    media: tuple[MediaBlob, ...] = (),
    briefing: str = "",
) -> Attempt:
    context = ExtractionContext(
        config=profile.config_for(pillar),
        transcript=transcript,
        mentions=said,
        media=media,
        briefing=briefing,
    )
    try:
        return Extracted(pillar=pillar, result=await engine.extract(context))
    except ModelUnavailableError as unavailable:
        _log.warning(
            "pillar extraction failed",
            extra={
                "pillar": pillar,
                "model": unavailable.model,
                "because": unavailable.because.value,
            },
        )
        return Failed(pillar=pillar, reason=FailureReason.model_error)
