from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from farkad_ai.models.cache import CachedModel, cache_key_of
from farkad_ai.models.port import ModelPort
from farkad_ai.pipeline.observer import TraceObserver
from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt, Usage


class DummySchema(BaseModel):
    message: str


class CountingModel(ModelPort):
    def __init__(self) -> None:
        self.calls = 0

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.calls += 1
        return Completion(
            value=schema.model_validate({"message": prompt.utterance}),
            usage=Usage(
                step=prompt.step,
                model="test-model",
                prompt_version=prompt.instructions_version,
                input_tokens=100,
                output_tokens=20,
                latency_ms=500,
                cost_cents=Decimal("0.05"),
            ),
        )


@pytest.mark.anyio
async def test_cached_model_miss_then_hit() -> None:
    observer = TraceObserver()
    inner = CountingModel()
    cached = CachedModel(inner, capacity=10, observer=observer)

    prompt = Prompt(
        step=PipelineStep.demo,
        instructions="Extract demo",
        instructions_version="v1",
        utterance="two eggs",
    )

    first = await cached.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert first.value.message == "two eggs"
    assert inner.calls == 1
    assert cached.hits == 0
    assert cached.misses == 1
    assert len(observer.cache_misses()) == 1
    assert len(observer.cache_hits()) == 0

    second = await cached.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert second.value.message == "two eggs"
    assert inner.calls == 1
    assert cached.hits == 1
    assert cached.misses == 1
    assert second.usage.latency_ms == 0
    assert second.usage.cost_cents == Decimal("0.0")
    assert len(observer.cache_hits()) == 1


@pytest.mark.anyio
async def test_cached_model_evicts_lru_when_capacity_exceeded() -> None:
    inner = CountingModel()
    cached = CachedModel(inner, capacity=2)

    p1 = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="1", utterance="1")
    p2 = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="1", utterance="2")
    p3 = Prompt(step=PipelineStep.demo, instructions="i", instructions_version="1", utterance="3")

    await cached.complete(p1, schema=DummySchema, tier=ModelTier.fast)
    await cached.complete(p2, schema=DummySchema, tier=ModelTier.fast)
    assert cached.size == 2

    await cached.complete(p3, schema=DummySchema, tier=ModelTier.fast)
    assert cached.size == 2

    await cached.complete(p1, schema=DummySchema, tier=ModelTier.fast)
    assert inner.calls == 4
    assert cached.misses == 4


@pytest.mark.anyio
async def test_cached_model_clear() -> None:
    inner = CountingModel()
    cached = CachedModel(inner, capacity=10)
    prompt = Prompt(
        step=PipelineStep.demo, instructions="i", instructions_version="1", utterance="eggs"
    )

    await cached.complete(prompt, schema=DummySchema, tier=ModelTier.fast)
    assert cached.size == 1
    assert cached.misses == 1

    cached.clear()
    assert cached.size == 0
    assert cached.hits == 0
    assert cached.misses == 0


def test_cache_key_is_deterministic() -> None:
    p1 = Prompt(
        step=PipelineStep.routing, instructions="i", instructions_version="v1", utterance="Two Eggs"
    )
    p2 = Prompt(
        step=PipelineStep.routing,
        instructions="i",
        instructions_version="v1",
        utterance="  two eggs  ",
    )
    assert cache_key_of(p1, DummySchema, ModelTier.fast) == cache_key_of(
        p2, DummySchema, ModelTier.fast
    )
