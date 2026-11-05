from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from google import genai
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from farkad_ai.models.factory import MissingCredentialsError
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

# Gemini's thinking budget in tokens: https://ai.google.dev/gemini-api/docs/thinking
THINKING_BUDGET: Mapping[Reasoning, int] = {
    Reasoning.none: 0,
    Reasoning.brief: 512,
    Reasoning.thorough: 2048,
}


@dataclass(frozen=True, slots=True)
class Retries:
    attempts: int
    first_wait: timedelta
    longest_wait: timedelta


class VertexModel(Model):
    default_choices: ClassVar[Mapping[ModelTier, ModelChoice]] = {
        ModelTier.fast: ModelChoice("gemini-3.5-flash-lite"),
        ModelTier.standard: ModelChoice("gemini-3.5-flash-lite", Reasoning.brief),
    }

    def __init__(self, client: genai.Client, *, choices: TierChoices | None = None) -> None:
        self._client = client
        self._choices = fixed(self.default_choices) if choices is None else choices

    @classmethod
    def connected(
        cls,
        *,
        project: str | None = None,
        location: str | None = None,
        retries: Retries | None = None,
    ) -> VertexModel:
        try:
            client = genai.Client(
                vertexai=True, project=project, location=location, http_options=_retrying(retries)
            )
        except (DefaultCredentialsError, ValueError) as error:
            raise MissingCredentialsError(
                "vertex", "GOOGLE_CLOUD_PROJECT set and `gcloud auth application-default login`"
            ) from error
        return cls(client)

    def choosing(self, choices: TierChoices) -> VertexModel:
        return VertexModel(self._client, choices=choices)

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        choice = await self._choices(tier)
        started = time.monotonic()
        try:
            response = await self._client.aio.models.generate_content(
                model=choice.model, contents=_parts(prompt), config=_asking(prompt, schema, choice)
            )
        except APIError as error:
            refusal = f"{type(error).__name__} {error.code}"
            raise ModelUnavailableError(
                tier, choice.model, Unavailability.provider_refused, refusal
            ) from error
        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            value = schema.model_validate(response.parsed)
        except ValidationError as error:
            raise ModelUnavailableError(
                tier, choice.model, Unavailability.output_did_not_parse, schema.__name__
            ) from error
        input_tokens, output_tokens = _tokens(response, tier, choice.model)
        usage = Usage.answering(
            prompt,
            model=choice.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
        return Completion(value=value, usage=usage)


def _asking(
    prompt: Prompt, schema: type[BaseModel], choice: ModelChoice
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=prompt.instructions,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        response_mime_type="application/json",
        response_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET[choice.reasoning]),
    )


def _tokens(
    response: types.GenerateContentResponse, tier: ModelTier, model: str
) -> tuple[int, int]:
    metadata = response.usage_metadata
    if (
        metadata is None
        or metadata.prompt_token_count is None
        or metadata.candidates_token_count is None
    ):
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "the response counted no tokens"
        )
    # `thoughts_token_count` is absent, not zero, without thinking: https://googleapis.github.io/python-genai/
    thoughts = metadata.thoughts_token_count or 0
    return metadata.prompt_token_count, metadata.candidates_token_count + thoughts


def _retrying(retries: Retries | None) -> types.HttpOptions | None:
    if retries is None:
        return None
    return types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=retries.attempts,
            initial_delay=retries.first_wait.total_seconds(),
            max_delay=retries.longest_wait.total_seconds(),
        )
    )


def _parts(prompt: Prompt) -> types.ContentListUnion:
    spoken = [types.Part.from_text(text=prompt.utterance)] if prompt.utterance else []
    sent: list[types.PartUnion] = [
        *spoken,
        *(
            types.Part.from_bytes(data=blob.data, mime_type=blob.content_type)
            for blob in prompt.media
        ),
    ]
    if not sent:
        sent.append(types.Part.from_text(text=PLACEHOLDER_INPUT))
    return sent
