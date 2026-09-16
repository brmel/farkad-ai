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
