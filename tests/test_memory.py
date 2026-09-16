from __future__ import annotations

import pytest

from farkad_ai.memory import (
    MAX_MEMORY_CONTENT_CHARS,
    MemoryCategory,
    MemoryItem,
    UserMemory,
)


def test_memory_item_validation() -> None:
    item = MemoryItem(
        id="mem-1",
        category=MemoryCategory.dietary,
        content="Lactose intolerant",
    )
    assert item.id == "mem-1"
    assert item.category == MemoryCategory.dietary
    assert item.content == "Lactose intolerant"
    assert item.enabled is True

    with pytest.raises(ValueError, match="id cannot be empty"):
        MemoryItem(id="  ", category=MemoryCategory.dietary, content="text")

    with pytest.raises(ValueError, match="content cannot be empty"):
        MemoryItem(id="mem-1", category=MemoryCategory.dietary, content="  ")

    with pytest.raises(ValueError, match="exceeds"):
        MemoryItem(
            id="mem-1",
            category=MemoryCategory.dietary,
            content="x" * (MAX_MEMORY_CONTENT_CHARS + 1),
        )


def test_user_memory_active_filtering() -> None:
    mem1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan", enabled=True)
    mem2 = MemoryItem(id="2", category=MemoryCategory.routine, content="Runs 5k", enabled=False)
    mem3 = MemoryItem(id="3", category=MemoryCategory.preference, content="Oat milk", enabled=True)
    memory = UserMemory(items=(mem1, mem2, mem3))

    assert len(memory.active_items) == 2
    assert memory.by_category(MemoryCategory.dietary) == (mem1,)
    assert memory.by_category(MemoryCategory.routine) == ()


def test_user_memory_with_and_without_item() -> None:
    mem1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan")
    memory = UserMemory().with_item(mem1)
    assert len(memory.items) == 1

    mem1_updated = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegetarian")
    memory = memory.with_item(mem1_updated)
    assert len(memory.items) == 1
    assert memory.items[0].content == "Vegetarian"

    memory = memory.without_item("1")
    assert len(memory.items) == 0


def test_as_prompt_context_formatting() -> None:
    mem1 = MemoryItem(id="1", category=MemoryCategory.dietary, content="Lactose intolerant")
    mem2 = MemoryItem(id="2", category=MemoryCategory.preference, content="Prefers oat milk")
    memory = UserMemory(items=(mem1, mem2))

    context = memory.as_prompt_context()
    assert "User Memory & Context:" in context
    assert "- [dietary] Lactose intolerant" in context
    assert "- [preference] Prefers oat milk" in context


def test_as_prompt_context_empty() -> None:
    assert UserMemory().as_prompt_context() == ""
    inactive = MemoryItem(id="1", category=MemoryCategory.dietary, content="Vegan", enabled=False)
    assert UserMemory(items=(inactive,)).as_prompt_context() == ""


def test_as_prompt_context_budget_truncation() -> None:
    items = tuple(
        MemoryItem(id=str(i), category=MemoryCategory.general, content=f"Fact number {i}")
        for i in range(10)
    )
    memory = UserMemory(items=items)
    context = memory.as_prompt_context(max_characters=60)
    assert len(context) <= 60


def test_memory_primitive_roundtrip() -> None:
    from farkad_ai.memory import memory_from_primitive, memory_to_primitive

    mem1 = MemoryItem(id="m1", category=MemoryCategory.dietary, content="Keto diet")
    mem2 = MemoryItem(
        id="m2", category=MemoryCategory.routine, content="Morning run", enabled=False
    )
    original = UserMemory(items=(mem1, mem2))

    primitives = memory_to_primitive(original)
    restored = memory_from_primitive(primitives)

    assert len(restored.items) == 2
    assert restored.items[0].id == "m1"
    assert restored.items[0].category == MemoryCategory.dietary
    assert restored.items[0].content == "Keto diet"
    assert restored.items[0].enabled is True
    assert restored.items[1].enabled is False


def test_user_memory_toggle_and_merge() -> None:
    mem1 = MemoryItem(id="m1", category=MemoryCategory.dietary, content="Keto diet")
    memory = UserMemory(items=(mem1,))

    toggled = memory.toggle_item("m1", False)
    assert toggled.items[0].enabled is False

    new_items = (
        MemoryItem(id="m2", category=MemoryCategory.dietary, content="keto diet"),  # duplicate
        MemoryItem(id="m3", category=MemoryCategory.preference, content="Decaf coffee"),
    )
    merged = memory.merge_new(new_items)
    assert len(merged.items) == 2
    assert merged.items[1].content == "Decaf coffee"


@pytest.mark.anyio
async def test_memory_inferrer_extracts_habits() -> None:
    from decimal import Decimal
    from pydantic import BaseModel
    from farkad_ai.memory import InferredMemories, MemoryCandidate, MemoryInferrer
    from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt, Usage

    class FakeMemoryModel:
        async def complete[T: BaseModel](
            self, prompt: Prompt, *, schema: type[T], tier: ModelTier
        ) -> Completion[T]:
            assert schema is InferredMemories
            assert tier == ModelTier.fast
            data = InferredMemories(
                memories=[
                    MemoryCandidate(category="dietary", content="Allergic to peanuts"),
                    MemoryCandidate(category="preference", content="Drinks oat milk"),
                ]
            )
            return Completion(
                value=data,  # type: ignore[arg-type]
                usage=Usage(
                    step=PipelineStep.extraction,
                    model="test-fast",
                    prompt_version="v1",
                    input_tokens=10,
                    output_tokens=5,
                    latency_ms=50,
                    cost_cents=Decimal("0.001"),
                ),
            )

    inferrer = MemoryInferrer(FakeMemoryModel())
    existing = UserMemory(
        items=(MemoryItem(id="e1", category=MemoryCategory.dietary, content="Allergic to peanuts"),)
    )
    inferred = await inferrer.infer("I drink oat milk and I cannot eat peanuts", existing)
    assert len(inferred) == 1
    assert inferred[0].category == MemoryCategory.preference
    assert inferred[0].content == "Drinks oat milk"
