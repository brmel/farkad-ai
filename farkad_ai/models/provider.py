from __future__ import annotations

import time
from abc import abstractmethod
from collections.abc import Collection
from typing import Any

from pydantic import BaseModel, ValidationError

from farkad_ai.models.port import ModelChoice, ModelPort, TierChoices
from farkad_ai.types import (
    Completion,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Reasoning,
    Unavailability,
    Usage,
)


class ProviderModel(ModelPort):
    honoured_reasoning: Collection[Reasoning]

    def __init__(self, *, sdk_installed: bool, sdk: str, extra: str, choices: TierChoices) -> None:
        if not sdk_installed:
            raise RuntimeError(
                f"{sdk} is required to use {type(self).__name__}. "
                f"Install with: pip install 'farkad-ai[{extra}]'"
            )
        self._choices = choices

    async def model_for(self, tier: ModelTier) -> str:
        return (await self._chosen(tier)).model

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        choice = await self._chosen(tier)
        model = choice.model
        started = time.monotonic()
        response = await self._send(prompt, schema=schema, tier=tier, choice=choice)
        latency_ms = int((time.monotonic() - started) * 1000)
        answer = self._answer(response, tier=tier, model=model)
        try:
            value = schema.model_validate(answer)
        except ValidationError as error:
            raise ModelUnavailableError(
                tier, model, Unavailability.output_did_not_parse, schema.__name__
            ) from error
        return Completion(
            value=value,
            usage=self._usage(
                response, prompt=prompt, tier=tier, model=model, latency_ms=latency_ms
            ),
        )

    async def _chosen(self, tier: ModelTier) -> ModelChoice:
        choice = await self._choices(tier)
        if choice.reasoning not in self.honoured_reasoning:
            raise ModelUnavailableError(
                tier,
                choice.model,
                Unavailability.unsupported_request,
                f"reasoning {choice.reasoning} with a forced structured answer",
            )
        return choice

    @abstractmethod
    async def _send(
        self, prompt: Prompt, *, schema: type[BaseModel], tier: ModelTier, choice: ModelChoice
    ) -> Any: ...

    @abstractmethod
    def _answer(self, response: Any, *, tier: ModelTier, model: str) -> object: ...

    @abstractmethod
    def _usage(
        self, response: Any, *, prompt: Prompt, tier: ModelTier, model: str, latency_ms: int
    ) -> Usage: ...
