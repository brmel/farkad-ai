from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from farkad_ai.types import (
    Completion,
    ModelTier,
    Prompt,
)


@dataclass(frozen=True, slots=True)
class TierChoice:
    model: str
    thinking_budget: int = 0


class TierChoices(Protocol):
    """Which model a tier runs, asked on every call so it can change without a restart."""

    async def __call__(self, tier: ModelTier) -> TierChoice: ...


def fixed(choices: Mapping[ModelTier, TierChoice]) -> TierChoices:
    async def choose(tier: ModelTier) -> TierChoice:
        return choices[tier]

    return choose


class ModelPort(Protocol):
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        """A fully parsed `schema` instance, never a partial one, or `ModelUnavailableError`."""
        ...
