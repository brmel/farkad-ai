"""The model reads meaning from one sentence; every rule about keeping it is `facts.learn`.

The model docstrings here reach Gemini as schema descriptions, so they are prompt text."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from farkad_ai.memory.facts import (
    MAX_CONTENT_CHARACTERS,
    Disclosure,
    Fact,
    MemoryCategory,
)
from farkad_ai.models.port import ModelPort
from farkad_ai.prompts import PromptAsset, prompt
from farkad_ai.types import ModelTier, PipelineStep, Prompt, Usage

INSTRUCTIONS = prompt("memory_inference")
MAX_SUBJECT_CHARACTERS = 40
NOTHING_KNOWN = "(nothing yet)"

_log = logging.getLogger(__name__)


class InferredFact(BaseModel):
    """One lasting fact about the person."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(description="snake_case topic in English; reuse a known one")
    category: MemoryCategory
    content: str = Field(
        max_length=MAX_CONTENT_CHARACTERS,
        description="The fact as one short sentence, in the language it was said",
    )


class InferredFacts(BaseModel):
    """Every lasting fact the sentence revealed; none for a one-off log."""

    model_config = ConfigDict(extra="forbid")

    facts: list[InferredFact]


@dataclass(frozen=True, slots=True)
class Inference:
    disclosures: tuple[Disclosure, ...]
    usage: Usage


class MemoryInferrer:
    def __init__(self, model: ModelPort, *, instructions: PromptAsset = INSTRUCTIONS) -> None:
        self._model = model
        self._asset = instructions

    async def infer(self, said: str, known: Iterable[Fact]) -> Inference:
        completion = await self._model.complete(
            Prompt(
                step=PipelineStep.memory,
                instructions=self._asset.format(known=_listed(known)),
                instructions_version=self._asset.version,
                utterance=said,
            ),
            schema=InferredFacts,
            tier=ModelTier.fast,
        )
        return Inference(
            disclosures=tuple(
                disclosure
                for inferred in completion.value.facts
                if (disclosure := _disclosed(inferred)) is not None
            ),
            usage=completion.usage,
        )


def subject_named(said: str) -> str:
    """Parsed here rather than in the schema: a pattern Gemini ignores fails the whole answer."""
    words = "".join(
        letter if letter.isascii() and letter.isalnum() else " " for letter in said.casefold()
    ).split()
    return "_".join(words)[:MAX_SUBJECT_CHARACTERS].strip("_")


def _disclosed(inferred: InferredFact) -> Disclosure | None:
    subject = subject_named(inferred.subject)
    if not subject or not inferred.content.strip():
        _log.warning("inferred fact dropped: no usable subject or content")
        return None
    return Disclosure(subject, inferred.category, inferred.content.strip())


def _listed(known: Iterable[Fact]) -> str:
    lines = [f"- {fact.subject}: {fact.disclosure.content}" for fact in known]
    return "\n".join(lines) if lines else NOTHING_KNOWN
