from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from farkad_ai.memory import (
    MAX_MEMORY_CONTENT_CHARS,
    InferredMemories,
    MemoryCandidate,
    MemoryCategory,
    MemoryInferrer,
    MemoryItem,
    UserMemory,
    memory_from_primitive,
    memory_to_primitive,
)
from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt, Usage


def test_memory_item_validation() -> None:
    item = MemoryItem(id="mem-1", category=MemoryCategory.dietary, content="Lactose intolerant")
    assert item.id == "mem-1" and item.category == MemoryCategory.dietary and item.enabled is True
    with pytest.raises(ValueError, match="id cannot be empty"):
        MemoryItem(id="  ", category=MemoryCategory.dietary, content="text")
    with pytest.raises(ValueError, match="content cannot be empty"):
        MemoryItem(id="mem-1", category=MemoryCategory.dietary, content="  ")
    with pytest.raises(ValueError, match="exceeds"):
        too_long = "x" * (MAX_MEMORY_CONTENT_CHARS + 1)
        MemoryItem(id="m1", category=MemoryCategory.dietary, content=too_long)


def test_user_memory_active_filtering() -> None:
    m1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan", enabled=True)
    m2 = MemoryItem(id="2", category=MemoryCategory.routine, content="Runs 5k", enabled=False)
    m3 = MemoryItem(id="3", category=MemoryCategory.preference, content="Oat milk", enabled=True)
    memory = UserMemory(items=(m1, m2, m3))
    assert len(memory.active_items) == 2
    assert memory.by_category(MemoryCategory.dietary) == (m1,)
    assert memory.by_category(MemoryCategory.routine) == ()


def test_user_memory_with_and_without_item() -> None:
    item1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan")
    mem = UserMemory().with_item(item1)
    assert len(mem.items) == 1
    mem = mem.with_item(MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegetarian"))
    assert len(mem.items) == 1 and mem.items[0].content == "Vegetarian"
    assert len(mem.without_item("1").items) == 0


def test_as_prompt_context_formatting() -> None:
    m1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Lactose intolerant")
    m2 = MemoryItem(id="2", category=MemoryCategory.preference, content="Prefers oat milk")
    ctx = UserMemory(items=(m1, m2)).as_prompt_context()
    assert "- [dietary] Lactose intolerant" in ctx and "- [preference] Prefers oat milk" in ctx


def test_as_prompt_context_empty() -> None:
    assert UserMemory().as_prompt_context() == ""
    inactive = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan", enabled=False)
    assert UserMemory(items=(inactive,)).as_prompt_context() == ""


def test_as_prompt_context_budget_truncation() -> None:
    items = tuple(
        MemoryItem(id=str(i), category=MemoryCategory.general, content=f"Fact {i}")
        for i in range(10)
    )
    assert len(UserMemory(items=items).as_prompt_context(max_characters=60)) <= 60


def test_memory_primitive_roundtrip() -> None:
    m1 = MemoryItem(id="m1", category=MemoryCategory.dietary, content="Keto diet")
    m2 = MemoryItem(id="m2", category=MemoryCategory.routine, content="Morning run", enabled=False)
    restored = memory_from_primitive(memory_to_primitive(UserMemory(items=(m1, m2))))
    assert len(restored.items) == 2 and restored.items[0].content == "Keto diet"
    assert restored.items[0].enabled is True and restored.items[1].enabled is False


def test_user_memory_toggle_and_merge() -> None:
    init_item = MemoryItem(id="m1", category=MemoryCategory.dietary, content="Keto diet")
    memory = UserMemory(items=(init_item,))
    assert memory.toggle_item("m1", False).items[0].enabled is False
    new_items = (
        MemoryItem(id="m2", category=MemoryCategory.dietary, content="keto diet"),
        MemoryItem(id="m3", category=MemoryCategory.preference, content="Decaf coffee"),
    )
    merged = memory.merge_new(new_items)
    assert len(merged.items) == 2 and merged.items[1].content == "Decaf coffee"


@pytest.mark.anyio
async def test_memory_inferrer_extracts_habits() -> None:
    class FakeMemoryModel:
        async def complete[T: BaseModel](
            self, prompt: Prompt, *, schema: type[T], tier: ModelTier
        ) -> Completion[T]:
            data = InferredMemories(
                memories=[
                    MemoryCandidate(category="dietary", content="Allergic to peanuts"),
                    MemoryCandidate(category="preference", content="Drinks oat milk"),
                ]
            )
            usage = Usage(
                step=PipelineStep.extraction,
                model="test-fast",
                prompt_version="v1",
                input_tokens=10,
                output_tokens=5,
                latency_ms=50,
                cost_cents=Decimal("0.001"),
            )
            return Completion(value=data, usage=usage)  # type: ignore[arg-type]

    inferrer = MemoryInferrer(FakeMemoryModel())
    existing = UserMemory(
        items=(MemoryItem(id="e1", category=MemoryCategory.dietary, content="Allergic to peanuts"),)
    )
    inferred = await inferrer.infer("I drink oat milk and I cannot eat peanuts", existing)
    assert len(inferred) == 1
    assert inferred[0].category == MemoryCategory.preference
    assert inferred[0].content == "Drinks oat milk"
