from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from farkad_ai.extraction.extractor import ask_for_entries
from farkad_ai.extraction.port import TrackedPillar
from farkad_ai.models.port import (
    Model,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Unavailability,
    Usage,
)
from farkad_ai.prompts import prompt

INSTRUCTIONS = prompt("recompute")


@dataclass(frozen=True, slots=True)
class _Recomputation:
    values: dict[str, object]
    usage: Usage


class EntryRecomputer:
    def __init__(self, model: Model) -> None:
        self._model = model

    async def recompute(
        self, pillar: TrackedPillar, stated: Mapping[str, object]
    ) -> _Recomputation:
        entries, usage = await ask_for_entries(
            self._model,
            INSTRUCTIONS,
            pillar,
            step=PipelineStep.recompute,
            tier=ModelTier.standard,
            stated=json.dumps(dict(stated), ensure_ascii=False, sort_keys=True),
        )
        if not entries:
            raise ModelUnavailableError(
                ModelTier.standard,
                usage.model,
                Unavailability.output_did_not_parse,
                f"no {pillar.pillar} entry recomputed",
            )
        return _Recomputation(values=entries[0], usage=usage)
