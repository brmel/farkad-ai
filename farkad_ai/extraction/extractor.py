from __future__ import annotations

import logging
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

from farkad_ai.extraction.port import (
    ExtractedEntry,
    ExtractionContext,
    ExtractionResult,
    TrackedPillar,
)
from farkad_ai.models.port import (
    Completion,
    MediaBlob,
    Model,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
    Usage,
)
from farkad_ai.prompts import PromptAsset, briefed, prompt, version_of

INSTRUCTIONS = prompt("extraction")

_log = logging.getLogger(__name__)


class PillarExtractor:
    def __init__(self, model: Model) -> None:
        self._model = model

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        try:
            return await self._extract_at(ModelTier.fast, context)
        except ModelUnavailableError as unavailable:
            if unavailable.because is not Unavailability.output_did_not_parse:
                raise
            _log.info(
                "extraction_tier_escalated",
                extra={"pillar": context.pillar.pillar, "model": unavailable.model},
            )
            return await self._extract_at(ModelTier.standard, context)

    async def _extract_at(self, tier: ModelTier, context: ExtractionContext) -> ExtractionResult:
        pillar = context.pillar
        entries, usage = await ask_for_entries(
            self._model,
            INSTRUCTIONS,
            pillar,
            step=PipelineStep.extraction,
            tier=tier,
            utterance="\n".join(context.mentions),
            media=context.media,
            briefing=context.briefing,
            log=context.transcript,
        )
        return ExtractionResult(
            pillar=pillar.pillar,
            entries=tuple(
                ExtractedEntry(values=entry, findings=tuple(pillar.review(entry)))
                for entry in entries
            ),
            usage=usage,
        )


async def ask_for_entries(
    model: Model,
    asset: PromptAsset,
    pillar: TrackedPillar,
    *,
    step: PipelineStep,
    tier: ModelTier,
    utterance: str = "",
    media: tuple[MediaBlob, ...] = (),
    briefing: str = "",
    **values: object,
) -> tuple[list[dict[str, object]], Usage]:
    completion: Completion[BaseModel] = await model.complete(
        Prompt(
            step=step,
            instructions=fill(asset, pillar, briefing=briefing, **values),
            instructions_version=version_of(
                asset.text, pillar.title, pillar.guidance, pillar.examples
            ),
            utterance=utterance,
            media=media,
        ),
        schema=answer_schema(pillar.entry_schema),
        tier=tier,
    )
    answered: list[dict[str, object]] = completion.value.model_dump(mode="json")["entries"]
    kept = [entry for entry in answered if _states_something(entry, pillar.label_fields)]
    return kept, completion.usage


def fill(asset: PromptAsset, pillar: TrackedPillar, *, briefing: str = "", **values: object) -> str:
    rendered = asset.format(
        title=pillar.title, guidance=pillar.guidance, examples=pillar.examples, **values
    )
    return briefed(rendered, briefing)


@lru_cache(maxsize=512)
def answer_schema(entry: type[BaseModel]) -> type[BaseModel]:
    one: Any = entry
    return create_model(
        "LogBatch",
        __config__=ConfigDict(extra="forbid"),
        entries=(list[one], Field(description="Every entry this utterance produced")),
    )


def _states_something(entry: Mapping[str, object], label_fields: frozenset[str]) -> bool:
    return any(value is not None for name, value in entry.items() if name not in label_fields)
