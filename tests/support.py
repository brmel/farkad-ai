from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from farkad_ai.extraction.port import Finding
from farkad_ai.models.port import ModelPort
from farkad_ai.types import (
    Completion,
    InputModality,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Unavailability,
    Usage,
)


def a_usage(step: StrEnum) -> Usage:
    return Usage(
        step=step,
        model="gemini-2.5-flash-lite",
        prompt_version="v1",
        input_modality=InputModality.text,
        input_tokens=10,
        output_tokens=5,
        latency_ms=100,
    )


class ScriptedModel(ModelPort):
    def __init__(self, answer: BaseModel | Mapping[str, object]) -> None:
        self._answer = answer
        self.asked: list[Prompt] = []

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.asked.append(prompt)
        return Completion(value=schema.model_validate(self._answer), usage=a_usage(prompt.step))


@dataclass(frozen=True, slots=True)
class Spec:
    pillar: str
    intent: str


class Registry:
    def __init__(self, *specs: Spec) -> None:
        self._specs = specs

    def __iter__(self) -> Iterator[Spec]:
        return iter(self._specs)

    def knows(self, route: str) -> bool:
        return any(spec.pillar == route for spec in self._specs)


class Item(BaseModel):
    pillar: str
    item: str | None = None


@dataclass(frozen=True, slots=True)
class Tracked:
    pillar: str
    title: str = "Items"
    guidance: str = "Record each item."
    examples: str = ""
    entry_schema: type[BaseModel] = Item
    flagged: tuple[Finding, ...] = ()

    def review(self, entry: Mapping[str, object]) -> Iterable[Finding]:
        return self.flagged


class AnswersByStep(ModelPort):
    """Answers each step with its own script; an `Unavailability` refuses that step."""

    def __init__(self, **answers: BaseModel | Mapping[str, object] | Unavailability) -> None:
        self._answers = answers
        self.asked: list[tuple[Prompt, ModelTier]] = []

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.asked.append((prompt, tier))
        match self._answers[prompt.step.value]:
            case Unavailability() as because:
                raise ModelUnavailableError(tier, f"model-{tier}", because, "detail")
            case answer:
                return Completion(value=schema.model_validate(answer), usage=a_usage(prompt.step))
