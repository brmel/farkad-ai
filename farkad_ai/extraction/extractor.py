from __future__ import annotations

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
from farkad_ai.models.port import ModelPort
from farkad_ai.prompts import PromptAsset, briefed, prompt
from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt

INSTRUCTIONS = prompt("extraction")
UNSTATED_FIELDS = frozenset({"pillar", "category"})


def holds_nothing(entry: Mapping[str, object]) -> bool:
    return not any(
        value is not None for name, value in entry.items() if name not in UNSTATED_FIELDS
    )


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


def entries_answered(completion: Completion[BaseModel]) -> list[dict[str, object]]:
    answered: list[dict[str, object]] = completion.value.model_dump(mode="json")["entries"]
    return [entry for entry in answered if not holds_nothing(entry)]


class PillarExtractor:
    def __init__(self, model: ModelPort, *, instructions: PromptAsset = INSTRUCTIONS) -> None:
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
                for entry in entries_answered(completion)
            ),
            usage=completion.usage,
        )
