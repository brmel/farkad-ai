from __future__ import annotations

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
)
from tests.support import ScriptedModel


class DummySchema(BaseModel):
    name: str


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


PROMPT = Prompt(step=PipelineStep.extraction, instructions="i", instructions_version="v1")


@pytest.mark.anyio
async def test_fallback_uses_primary_when_available() -> None:
    primary = ScriptedModel({"name": "primary"})
    secondary = ScriptedModel({"name": "secondary"})
    model = FallbackModel(primary, secondary)

    res = await model.complete(PROMPT, schema=DummySchema, tier=ModelTier.fast)
    assert res.value.name == "primary"
    assert len(primary.asked) == 1
    assert secondary.asked == []


@pytest.mark.anyio
async def test_fallback_switches_to_secondary_when_primary_fails() -> None:
    primary = FailingModel("primary")
    secondary = ScriptedModel({"name": "secondary"})
    model = FallbackModel(primary, secondary)

    res = await model.complete(PROMPT, schema=DummySchema, tier=ModelTier.fast)
    assert res.value.name == "secondary"
    assert primary.calls == 1
    assert len(secondary.asked) == 1


@pytest.mark.anyio
async def test_fallback_raises_when_both_fail() -> None:
    model = FallbackModel(FailingModel("primary"), FailingModel("secondary"))

    with pytest.raises(ModelUnavailableError) as exc_info:
        await model.complete(PROMPT, schema=DummySchema, tier=ModelTier.fast)
    assert exc_info.value.model == "secondary"
