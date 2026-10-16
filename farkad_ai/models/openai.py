from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any

from openai import APIError, AsyncOpenAI
from openai.types.chat import (
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
)
from pydantic import BaseModel

from farkad_ai.models.port import (
    MediaBlob,
    MediaType,
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
from farkad_ai.models.provider import PLACEHOLDER_INPUT, ProviderModel

DEFAULT_CHOICES: Mapping[ModelTier, ModelChoice] = {
    ModelTier.fast: ModelChoice("gpt-4o-mini"),
    ModelTier.standard: ModelChoice("gpt-4o"),
}


class OpenAIModel(ProviderModel):
    honoured_reasoning = (Reasoning.none,)

    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        choices: TierChoices | None = None,
    ) -> None:
        super().__init__(choices or fixed(DEFAULT_CHOICES))
        self._client = client

    async def _send(
        self,
        prompt: Prompt,
        *,
        schema: type[BaseModel],
        tier: ModelTier,
        choice: ModelChoice,
    ) -> Any:
        model = choice.model
        messages = _messages(prompt, tier=tier, model=model)
        try:
            return await self._client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
            )
        except APIError as error:
            raise ModelUnavailableError(
                tier,
                model,
                Unavailability.provider_refused,
                str(error),
            ) from error

    def _answer(self, response: Any, *, tier: ModelTier, model: str) -> object:
        if not response.choices:
            raise ModelUnavailableError(
                tier, model, Unavailability.output_did_not_parse, "no choices in response"
            )
        message = response.choices[0].message
        if message.refusal:
            raise ModelUnavailableError(
                tier, model, Unavailability.provider_refused, f"refusal: {message.refusal}"
            )
        if message.parsed is None:
            raise ModelUnavailableError(
                tier, model, Unavailability.output_did_not_parse, "no parsed object in message"
            )
        return message.parsed

    def _usage(
        self, response: Any, *, prompt: Prompt, tier: ModelTier, model: str, latency_ms: int
    ) -> Usage:
        if response.usage is None:
            raise ModelUnavailableError(
                tier, model, Unavailability.usage_not_reported, "no usage in response"
            )
        return Usage.answering(
            prompt,
            model=model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
        )


def _messages(prompt: Prompt, *, tier: ModelTier, model: str) -> list[ChatCompletionMessageParam]:
    user_parts: list[ChatCompletionContentPartParam] = []
    if prompt.utterance:
        user_parts.append({"type": "text", "text": prompt.utterance})
    user_parts.extend(_image_part(blob, tier=tier, model=model) for blob in prompt.media)
    return [
        {"role": "system", "content": prompt.instructions},
        {"role": "user", "content": user_parts or [{"type": "text", "text": PLACEHOLDER_INPUT}]},
    ]


def _image_part(
    blob: MediaBlob, *, tier: ModelTier, model: str
) -> ChatCompletionContentPartImageParam:
    match blob.content_type:
        case MediaType.image_jpeg | MediaType.image_png:
            encoded = base64.b64encode(blob.data).decode("ascii")
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{blob.content_type.value};base64,{encoded}"},
            }
        case MediaType.audio_aac:
            raise ModelUnavailableError(
                tier, model, Unavailability.provider_refused, "audio input unsupported"
            )
