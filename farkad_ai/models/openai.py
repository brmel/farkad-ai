from __future__ import annotations

import base64
import time
from collections.abc import Mapping
from typing import Any

try:
    import openai  # type: ignore[import-not-found]
    from openai import APIError as OpenAIAPIError
    from openai import AsyncOpenAI

    _OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    AsyncOpenAI = Any
    OpenAIAPIError = Exception
    _OPENAI_AVAILABLE = False

from pydantic import BaseModel, ValidationError

from farkad_ai.models.port import ModelPort, TierChoice, TierChoices, fixed
from farkad_ai.types import (
    Completion,
    MediaBlob,
    MediaType,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Unavailability,
    Usage,
)

DEFAULT_OPENAI_MODELS: Mapping[ModelTier, TierChoice] = {
    ModelTier.fast: TierChoice("gpt-4o-mini"),
    ModelTier.standard: TierChoice("gpt-4o"),
}


class OpenAIModel(ModelPort):
    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        choices: TierChoices | None = None,
    ) -> None:
        if not _OPENAI_AVAILABLE:
            raise RuntimeError(
                "openai is required to use OpenAIModel. "
                "Install with: pip install 'farkad-ai[openai]'"
            )
        self._client = client
        self._choices = choices or fixed(DEFAULT_OPENAI_MODELS)

    async def model_for(self, tier: ModelTier) -> str:
        return (await self._choices(tier)).model

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        model = await self.model_for(tier)
        started = time.monotonic()
        response = await self._send(prompt, schema=schema, model=model, tier=tier)
        latency_ms = int((time.monotonic() - started) * 1000)
        value = extract_parsed_choice(schema, response, tier=tier, model=model)
        return Completion(
            value=value,
            usage=usage_from_openai(
                response, prompt=prompt, tier=tier, model=model, latency_ms=latency_ms
            ),
        )

    async def _send(
        self,
        prompt: Prompt,
        *,
        schema: type[BaseModel],
        model: str,
        tier: ModelTier,
    ) -> Any:
        messages = build_openai_messages(prompt, tier=tier, model=model)
        try:
            return await self._client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
            )
        except OpenAIAPIError as error:
            raise ModelUnavailableError(
                tier,
                model,
                Unavailability.provider_refused,
                str(error),
            ) from error


def build_openai_messages(prompt: Prompt, *, tier: ModelTier, model: str) -> list[dict[str, Any]]:
    system_message = {"role": "system", "content": prompt.instructions}
    user_parts: list[dict[str, Any]] = []
    if prompt.utterance:
        user_parts.append({"type": "text", "text": prompt.utterance})
    user_parts.extend(image_part(blob, tier=tier, model=model) for blob in prompt.media)
    user_message = {"role": "user", "content": user_parts or [{"type": "text", "text": "Input."}]}
    return [system_message, user_message]


def image_part(blob: MediaBlob, *, tier: ModelTier, model: str) -> dict[str, Any]:
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


def extract_parsed_choice[T: BaseModel](
    schema: type[T], response: Any, *, tier: ModelTier, model: str
) -> T:
    if not response.choices:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, "no choices in response"
        )
    message = response.choices[0].message
    if message.refusal:
        raise ModelUnavailableError(
            tier, model, Unavailability.provider_refused, f"refusal: {message.refusal}"
        )
    parsed = message.parsed
    if parsed is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, "no parsed object in message"
        )
    try:
        return schema.model_validate(parsed)
    except ValidationError as error:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, schema.__name__
        ) from error


def usage_from_openai(
    response: Any,
    *,
    prompt: Prompt,
    tier: ModelTier,
    model: str,
    latency_ms: int,
) -> Usage:
    if response.usage is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "no usage in response"
        )
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    return Usage.answering(
        prompt,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
