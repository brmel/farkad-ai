"""Docstrings and descriptions here reach the model in its answer schema: they are prompt text."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model

from farkad_ai.memory.facts import Disclosure, Fact
from farkad_ai.models.port import Model, ModelTier, PipelineStep, Prompt, Usage
from farkad_ai.prompts import prompt

INSTRUCTIONS = prompt("memory_inference")
MAX_SUBJECT_CHARACTERS = 40
NOTHING_KNOWN = "(nothing yet)"
NOTHING_SWITCHED_OFF = "(none)"
CONTENT_DESCRIPTION = "The fact as one short sentence, in the language it was said"

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StatedDay:
    phrase: str
    day_offset: int


class InferredEnd(BaseModel):
    """When the person said the fact stops applying."""

    model_config = ConfigDict(extra="forbid")

    phrase: str = Field(description="Their words for the end, exactly as said")
    day_offset: int = Field(description="Days from today to the last day it applies")

    def stated(self) -> StatedDay:
        return StatedDay(phrase=self.phrase, day_offset=self.day_offset)


class InferredFact(BaseModel):
    """One lasting fact about the person."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(description="snake_case topic in English; reuse a known one")
    category: str
    content: str = Field(description=CONTENT_DESCRIPTION)
    until: InferredEnd | None = Field(
        default=None, description="Only when the person bounded the fact in time; null otherwise"
    )
    asked_to_remember: bool = Field(
        description="True only when the person explicitly asked for this to be remembered"
    )


class InferredFacts(BaseModel):
    """Every lasting fact the sentence revealed; none for a one-off log."""

    model_config = ConfigDict(extra="forbid")

    facts: list[InferredFact]


@dataclass(frozen=True, slots=True)
class Statement[Category: StrEnum]:
    disclosure: Disclosure[Category]
    until: StatedDay | None
    asked_to_remember: bool


@dataclass(frozen=True, slots=True)
class Inference[Category: StrEnum]:
    statements: tuple[Statement[Category], ...]
    usage: Usage


class MemoryInferrer[Category: StrEnum]:
    def __init__(
        self,
        model: Model,
        *,
        categories: type[Category],
        max_content_characters: int,
    ) -> None:
        self._model = model
        self._categories = categories
        self._schema = _answer_schema(categories, max_content_characters)

    async def infer(
        self, said: str, known: Iterable[Fact[Category]], *, switched_off: Iterable[str]
    ) -> Inference[Category]:
        known = tuple(known)
        completion = await self._model.complete(
            Prompt(
                step=PipelineStep.memory,
                instructions=INSTRUCTIONS.format(
                    categories=_either(self._categories),
                    known=_listed(known),
                    switched_off=", ".join(switched_off) or NOTHING_SWITCHED_OFF,
                ),
                instructions_version=INSTRUCTIONS.version,
                utterance=said,
            ),
            schema=self._schema,
            tier=ModelTier.fast,
        )
        subjects = _subjects_of(known)
        return Inference(
            statements=tuple(
                statement
                for inferred in completion.value.facts
                if (statement := self._stated(inferred, subjects)) is not None
            ),
            usage=completion.usage,
        )

    def _stated(
        self, inferred: InferredFact, known: Mapping[str, str]
    ) -> Statement[Category] | None:
        subject = known.get(inferred.subject.casefold()) or subject_named(inferred.subject)
        if not subject or not inferred.content.strip():
            _log.warning("inferred fact dropped: no usable subject or content")
            return None
        return Statement(
            Disclosure(subject, self._categories(inferred.category), inferred.content.strip()),
            until=None if inferred.until is None else inferred.until.stated(),
            asked_to_remember=inferred.asked_to_remember,
        )


def subject_named(said: str) -> str:
    """Parsed here rather than in the schema: a pattern Gemini ignores fails the whole answer."""
    words = "".join(
        letter if letter.isascii() and letter.isalnum() else " " for letter in said.casefold()
    ).split()
    return "_".join(words)[:MAX_SUBJECT_CHARACTERS].strip("_")


def _answer_schema(categories: type[StrEnum], max_content_characters: int) -> type[InferredFacts]:
    fact = create_model(
        InferredFact.__name__,
        __base__=InferredFact,
        __doc__=InferredFact.__doc__,
        category=(categories, ...),
        content=(str, Field(max_length=max_content_characters, description=CONTENT_DESCRIPTION)),
    )
    each: Any = fact
    return create_model(
        InferredFacts.__name__,
        __base__=InferredFacts,
        __doc__=InferredFacts.__doc__,
        facts=(list[each], ...),
    )


def _either(categories: type[StrEnum]) -> str:
    *first, last = (category.value for category in categories)
    return f"{', '.join(first)} or {last}" if first else last


def _subjects_of(known: Iterable[Fact[StrEnum]]) -> dict[str, str]:
    return {fact.subject.casefold(): fact.subject for fact in known}


def _listed(known: Iterable[Fact[StrEnum]]) -> str:
    lines = [f"- {fact.subject}: {fact.disclosure.content}" for fact in known]
    return "\n".join(lines) if lines else NOTHING_KNOWN
