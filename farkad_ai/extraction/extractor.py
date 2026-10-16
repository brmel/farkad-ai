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
    Model,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
)
from farkad_ai.prompts import PromptAsset, briefed, prompt

INSTRUCTIONS = prompt("extraction")

_log = logging.getLogger(__name__)


class PillarExtractor:
    def __init__(self, model: Model, *, instructions: PromptAsset = INSTRUCTIONS) -> None:
        self._model = model
        self._asset = instructions

    async def extract(
        self, context: ExtractionContext, *, tier: ModelTier = ModelTier.standard
    ) -> ExtractionResult:
        pillar = context.pillar
        completion: Completion[BaseModel] = await self._model.complete(
            Prompt(
                step=PipelineStep.extraction,
                instructions=fill(
                    self._asset, pillar, briefing=context.briefing, log=context.transcript
                ),
                instructions_version=self._asset.version,
                utterance="\n".join(context.mentions),
                media=context.media,
            ),
            schema=answer_schema(pillar.entry_schema),
            tier=tier,
        )
        return ExtractionResult(
            pillar=pillar.pillar,
            entries=tuple(
                ExtractedEntry(values=entry, findings=tuple(pillar.review(entry)))
                for entry in entries_answered(completion, pillar)
            ),
            usage=completion.usage,
        )

    async def extract_escalating(self, context: ExtractionContext) -> ExtractionResult:
        try:
            return await self.extract(context, tier=ModelTier.fast)
        except ModelUnavailableError as unavailable:
            if unavailable.because is not Unavailability.output_did_not_parse:
                raise
            _log.info(
                "extraction_tier_escalated",
                extra={"pillar": context.pillar.pillar, "model": unavailable.model},
            )
            return await self.extract(context, tier=ModelTier.standard)


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


def entries_answered(
    completion: Completion[BaseModel], pillar: TrackedPillar
) -> list[dict[str, object]]:
    answered: list[dict[str, object]] = completion.value.model_dump(mode="json")["entries"]
    return [entry for entry in answered if _states_something(entry, pillar.label_fields)]


def _states_something(entry: Mapping[str, object], label_fields: frozenset[str]) -> bool:
    return any(value is not None for name, value in entry.items() if name not in label_fields)
