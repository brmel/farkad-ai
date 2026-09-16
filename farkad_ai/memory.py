from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, Field

from farkad_ai.models.port import ModelPort
from farkad_ai.types import ModelTier, Prompt


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

    def toggle_item(self, item_id: str, enabled: bool) -> UserMemory:
        return UserMemory(
            items=tuple(
                MemoryItem(
                    id=item.id,
                    category=item.category,
                    content=item.content,
                    enabled=enabled,
                    confidence=item.confidence,
                    updated_at=item.updated_at,
                )
                if item.id == item_id
                else item
                for item in self.items
            )
        )

    def merge_new(self, items: tuple[MemoryItem, ...]) -> UserMemory:
        existing_contents = {item.content.lower().strip() for item in self.items}
        added: list[MemoryItem] = []
        for item in items:
            normalized = item.content.lower().strip()
            if normalized not in existing_contents:
                added.append(item)
                existing_contents.add(normalized)
        return UserMemory(items=(*self.items, *added))

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


def memory_from_primitive(raw: object) -> UserMemory:
    match raw:
        case list() as entries:
            items: list[MemoryItem] = []
            for entry in entries:
                match entry:
                    case {
                        "id": str(item_id),
                        "category": str(cat_name),
                        "content": str(content),
                    }:
                        if cat_name in MemoryCategory._value2member_map_:
                            category = MemoryCategory(cat_name)
                            enabled = bool(entry.get("enabled", True))
                            confidence = float(entry.get("confidence", 1.0))
                            updated_at = entry.get("updated_at")
                            items.append(
                                MemoryItem(
                                    id=item_id,
                                    category=category,
                                    content=content,
                                    enabled=enabled,
                                    confidence=confidence,
                                    updated_at=str(updated_at) if updated_at else None,
                                )
                            )
            return UserMemory(items=tuple(items))
        case _:
            return UserMemory()


def memory_to_primitive(memory: UserMemory) -> list[dict[str, object]]:
    return [
        {
            "id": item.id,
            "category": item.category.value,
            "content": item.content,
            "enabled": item.enabled,
            "confidence": item.confidence,
            "updated_at": item.updated_at,
        }
        for item in memory.items
    ]


MEMORY_INFERENCE_INSTRUCTIONS = (
    "Analyze the user utterance. If it mentions recurring personal habits, dietary restrictions, "
    "routines, medical constraints, or preferences to remember for the future, extract them. "
    "If it is only a single one-time log (e.g. 'I ate 2 eggs', 'ran 5km'), return an empty list. "
    "Categories must be one of: 'dietary', 'routine', 'preference', 'medical', 'general'."
)


class MemoryCandidate(BaseModel):
    category: str
    content: str


class InferredMemories(BaseModel):
    memories: list[MemoryCandidate] = Field(default_factory=list)


class MemoryInferrer:
    def __init__(self, model: ModelPort) -> None:
        self._model = model

    async def infer(self, text: str, existing: UserMemory) -> tuple[MemoryItem, ...]:
        from farkad_ai.types import Completion, PipelineStep

        stripped = text.strip()
        if not stripped or len(stripped) < 5:
            return ()
        prompt = Prompt(
            step=PipelineStep.extraction,
            instructions=MEMORY_INFERENCE_INSTRUCTIONS,
            instructions_version="v1",
            utterance=stripped,
        )
        try:
            completion: Completion[InferredMemories] = await self._model.complete(
                prompt,
                schema=InferredMemories,
                tier=ModelTier.fast,
            )
            return self._to_items(completion.value.memories, existing)
        except Exception:
            return ()

    def _to_items(
        self, candidates: list[MemoryCandidate], existing: UserMemory
    ) -> tuple[MemoryItem, ...]:
        existing_contents = {item.content.lower().strip() for item in existing.items}
        inferred: list[MemoryItem] = []
        for candidate in candidates:
            normalized = candidate.content.strip()
            if not normalized or normalized.lower() in existing_contents:
                continue
            if candidate.category in MemoryCategory._value2member_map_:
                category = MemoryCategory(candidate.category)
                item_id = hashlib.sha256(normalized.encode()).hexdigest()[:12]
                inferred.append(MemoryItem(id=item_id, category=category, content=normalized))
                existing_contents.add(normalized.lower())
        return tuple(inferred)
