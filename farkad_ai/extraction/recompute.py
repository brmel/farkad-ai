from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from farkad_ai.extraction.extractor import answer_schema, entries_answered, fill, pillar_version
from farkad_ai.extraction.port import TrackedPillar
from farkad_ai.models.port import (
    Completion,
    Model,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
    Usage,
)
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
                instructions_version=pillar_version(INSTRUCTIONS, pillar),
            ),
            schema=answer_schema(pillar.entry_schema),
            tier=ModelTier.standard,
        )
        entries = entries_answered(completion, pillar)
        if not entries:
            raise ModelUnavailableError(
                ModelTier.standard,
                completion.usage.model,
                Unavailability.output_did_not_parse,
                f"no {pillar.pillar} entry recomputed",
            )
        return Recomputation(values=entries[0], usage=completion.usage)
