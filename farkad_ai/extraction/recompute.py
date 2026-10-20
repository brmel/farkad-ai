from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from farkad_ai.extraction.extractor import answer_schema, entries_answered, fill
from farkad_ai.extraction.port import TrackedPillar
from farkad_ai.models.port import Completion, Model, ModelTier, PipelineStep, Prompt, Usage
from farkad_ai.prompts import prompt

INSTRUCTIONS = prompt("recompute")


@dataclass(frozen=True, slots=True)
class Recomputation:
    values: dict[str, object]
    usage: Usage


class EntryRecomputer:
    def __init__(self, model: Model) -> None:
        self._model = model

    async def recompute(self, pillar: TrackedPillar, stated: Mapping[str, object]) -> Recomputation:
        completion: Completion[BaseModel] = await self._model.complete(
            Prompt(
                step=PipelineStep.recompute,
                instructions=fill(
                    INSTRUCTIONS,
                    pillar,
                    stated=json.dumps(dict(stated), ensure_ascii=False, sort_keys=True),
                ),
                instructions_version=INSTRUCTIONS.version,
            ),
            schema=answer_schema(pillar.entry_schema),
            tier=ModelTier.standard,
        )
        return Recomputation(
            values=next(iter(entries_answered(completion, pillar)), {}),
            usage=completion.usage,
        )
