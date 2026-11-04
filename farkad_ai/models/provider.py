from __future__ import annotations

import time
from abc import abstractmethod
from collections.abc import Collection, Mapping
from typing import ClassVar

from pydantic import BaseModel, ValidationError

from farkad_ai.models.port import (
    Completion,
    Model,
    ModelChoice,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Reasoning,
    TierChoices,
    Unavailability,
    Usage,
    fixed,
)

PLACEHOLDER_INPUT = "Input."


class MissingCredentialsError(Exception):
    def __init__(self, provider: str, remedy: str) -> None:
        super().__init__(f"the {provider} provider needs {remedy}")


class ProviderModel[Client, Response, Refusal: Exception](Model):
    honoured_reasoning: Collection[Reasoning]
    default_choices: ClassVar[Mapping[ModelTier, ModelChoice]]
    refused_by: type[Refusal]

    def __init__(self, client: Client, *, choices: TierChoices | None = None) -> None:
        self._client = client
        self._choices = fixed(self.default_choices) if choices is None else choices

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        choice = await self._chosen(tier)
        model = choice.model
        started = time.monotonic()
        try:
            response = await self._send(prompt, schema=schema, tier=tier, choice=choice)
        except self.refused_by as error:
            raise ModelUnavailableError(
                tier, model, Unavailability.provider_refused, self._refusal(error)
            ) from error
        latency_ms = int((time.monotonic() - started) * 1000)
        answer = self._answer(response, tier=tier, model=model)
        try:
            value = schema.model_validate(answer)
        except ValidationError as error:
            raise ModelUnavailableError(
                tier, model, Unavailability.output_did_not_parse, schema.__name__
            ) from error
        tokens = self._tokens(response)
        if tokens is None:
            raise ModelUnavailableError(
                tier, model, Unavailability.usage_not_reported, "the response counted no tokens"
            )
        input_tokens, output_tokens = tokens
        usage = Usage.answering(
            prompt,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
        return Completion(value=value, usage=usage)

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
    ) -> Response: ...

    @abstractmethod
    def _answer(self, response: Response, *, tier: ModelTier, model: str) -> object: ...

    @abstractmethod
    def _tokens(self, response: Response) -> tuple[int, int] | None: ...

    def _refusal(self, error: Refusal) -> str:
        return str(error)
