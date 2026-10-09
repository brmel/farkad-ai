from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from farkad_ai.extraction.port import (
    ExtractedEntry,
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
)
from farkad_ai.models.port import ModelPort
from farkad_ai.types import (
    Completion,
    InputModality,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
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


@dataclass(frozen=True, slots=True)
class PillarConfig:
    pillar: str


class Profile:
    def __init__(self, *tracked: str) -> None:
        self._tracked = frozenset(tracked)

    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars & self._tracked

    def config_for(self, pillar: str) -> PillarConfig:
        return PillarConfig(pillar)


class SuccessfulExtractor(PillarExtractionPort[PillarConfig]):
    def __init__(self, label: str) -> None:
        self.label = label
        self.calls = 0
        self.told: dict[str, tuple[str, ...]] = {}

    async def extract(self, context: ExtractionContext[PillarConfig]) -> ExtractionResult:
        self.calls += 1
        self.told[context.config.pillar] = context.mentions
        return ExtractionResult(
            pillar=context.config.pillar,
            entries=(ExtractedEntry(values={"item": self.label}, findings=()),),
            usage=a_usage(PipelineStep.extraction),
        )


class RefusingExtractor(PillarExtractionPort[PillarConfig]):
    def __init__(self, because: Unavailability) -> None:
        self.because = because
        self.calls = 0

    async def extract(self, context: ExtractionContext[PillarConfig]) -> ExtractionResult:
        self.calls += 1
        raise ModelUnavailableError(ModelTier.fast, "model-fast", self.because, "detail")
