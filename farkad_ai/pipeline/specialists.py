from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from farkad_ai.extraction.port import ExtractionContext, ExtractionResult, PillarExtractionPort
from farkad_ai.pipeline.types import CaptureProfileProtocol, FailureReason
from farkad_ai.types import MediaBlob, ModelUnavailableError


@dataclass(frozen=True, slots=True)
class Extracted:
    pillar: str
    result: ExtractionResult


@dataclass(frozen=True, slots=True)
class Failed:
    pillar: str
    reason: FailureReason


Attempt = Extracted | Failed


async def extract_each(
    engine: PillarExtractionPort,
    pillars: Sequence[str],
    transcript: str,
    profile: CaptureProfileProtocol,
    media: tuple[MediaBlob, ...] = (),
    memory_context: str = "",
) -> list[Attempt]:
    return list(
        await asyncio.gather(
            *(
                _attempt(
                    engine,
                    pillar,
                    transcript,
                    profile,
                    media=media,
                    memory_context=memory_context,
                )
                for pillar in pillars
            )
        )
    )


async def _attempt(
    engine: PillarExtractionPort,
    pillar: str,
    transcript: str,
    profile: CaptureProfileProtocol,
    media: tuple[MediaBlob, ...] = (),
    memory_context: str = "",
) -> Attempt:
    context = ExtractionContext(
        config=profile.config_for(pillar),
        transcript=transcript,
        media=media,
        memory_context=memory_context,
    )
    try:
        return Extracted(pillar=pillar, result=await engine.extract(context))
    except ModelUnavailableError:
        return Failed(pillar=pillar, reason=FailureReason.model_error)
