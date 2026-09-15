from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from farkad_ai.types import (
    Completion,
    ModelTier,
    Prompt,
)


class ModelPort(Protocol):
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        """A fully parsed `schema` instance or raises ModelUnavailableError."""
        ...
