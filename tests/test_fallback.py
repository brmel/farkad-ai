from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from farkad_ai.models.fallback import FallbackModel
from farkad_ai.models.port import ModelPort
from farkad_ai.types import (
    Completion,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
    Usage,
)


class DummySchema(BaseModel):
    name: str


class ConstantModel(ModelPort):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.calls += 1
        return Completion(
            value=schema.model_validate({"name": self.name}),
            usage=Usage(
                step=prompt.step,
                model=self.name,
                prompt_version=prompt.instructions_version,
                input_tokens=10,
                output_tokens=5,
                latency_ms=100,
                cost_cents=Decimal("0.01"),
            ),
        )


class FailingModel(ModelPort):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.calls += 1
        raise ModelUnavailableError(
            tier, self.name, Unavailability.provider_refused, "rate limited"
        )


@pytest.mark.anyio
async def test_fallback_uses_primary_when_available() -> None:
    primary = ConstantModel("primary")
    secondary = ConstantModel("secondary")
    model = FallbackModel(primary, secondary)
    prompt = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="v1")

    res = await model.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert res.value.name == "primary"
    assert primary.calls == 1
    assert secondary.calls == 0


@pytest.mark.anyio
async def test_fallback_switches_to_secondary_when_primary_fails() -> None:
    primary = FailingModel("primary")
    secondary = ConstantModel("secondary")
    model = FallbackModel(primary, secondary)
    prompt = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="v1")

    res = await model.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert res.value.name == "secondary"
    assert primary.calls == 1
    assert secondary.calls == 1


@pytest.mark.anyio
async def test_fallback_raises_when_both_fail() -> None:
    primary = FailingModel("primary")
    secondary = FailingModel("secondary")
    model = FallbackModel(primary, secondary)
    prompt = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="v1")

    with pytest.raises(ModelUnavailableError) as exc_info:
        await model.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert exc_info.value.model == "secondary"
