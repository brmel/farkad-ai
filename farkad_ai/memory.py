from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MemoryCategory(StrEnum):
    dietary = "dietary"
    routine = "routine"
    preference = "preference"
    medical = "medical"
    general = "general"


MAX_MEMORY_CONTENT_CHARS = 250
MAX_ACTIVE_MEMORY_ITEMS = 20


@dataclass(frozen=True, slots=True)
class MemoryItem:
    id: str
    category: MemoryCategory
    content: str
    enabled: bool = True
    confidence: float = 1.0
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("memory id cannot be empty")
        stripped = self.content.strip()
        if not stripped:
            raise ValueError("memory content cannot be empty")
        if len(stripped) > MAX_MEMORY_CONTENT_CHARS:
            raise ValueError(f"memory content exceeds {MAX_MEMORY_CONTENT_CHARS} characters")


@dataclass(frozen=True, slots=True)
class UserMemory:
    items: tuple[MemoryItem, ...] = field(default_factory=tuple)

    @property
    def active_items(self) -> tuple[MemoryItem, ...]:
        return tuple(item for item in self.items if item.enabled)

    def by_category(self, category: MemoryCategory) -> tuple[MemoryItem, ...]:
        return tuple(item for item in self.active_items if item.category == category)

    def with_item(self, item: MemoryItem) -> UserMemory:
        filtered = tuple(existing for existing in self.items if existing.id != item.id)
        return UserMemory(items=(*filtered, item))

    def without_item(self, item_id: str) -> UserMemory:
        return UserMemory(items=tuple(item for item in self.items if item.id != item_id))

    def as_prompt_context(self, *, max_items: int = 10, max_characters: int = 600) -> str:
        active = self.active_items[:max_items]
        if not active:
            return ""
        lines: list[str] = ["User Memory & Context:"]
        total_chars = len(lines[0])
        for item in active:
            line = f"- [{item.category.value}] {item.content.strip()}"
            if total_chars + len(line) + 1 > max_characters:
                break
            lines.append(line)
            total_chars += len(line) + 1
        return "\n".join(lines) if len(lines) > 1 else ""
