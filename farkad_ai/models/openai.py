from __future__ import annotations

import base64
import time
from collections.abc import Callable, Mapping
from typing import Any

try:
    import openai  # type: ignore[import-not-found]
    from openai import AsyncOpenAI
    from openai import APIError as OpenAIAPIError

    _OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    AsyncOpenAI = Any
    OpenAIAPIError = Exception
    _OPENAI_AVAILABLE = False

from pydantic import BaseModel, ValidationError

from farkad_ai.models.port import ModelPort
from farkad_ai.models.pricing import modality_of, price_of
from farkad_ai.types import (
    Completion,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Unavailability,
    Usage,
)

DEFAULT_OPENAI_MODELS: Mapping[ModelTier, str] = {
    ModelTier.fast: "gpt-4o-mini",
    ModelTier.standard: "gpt-4o",
}


class OpenAIModel(ModelPort):
    def __init__(
        self,
        client: AsyncOpenAI,
        *,
        model_resolver: Callable[[ModelTier], str] | None = None,
    ) -> None:
        if not _OPENAI_AVAILABLE:
            raise RuntimeError(
                "openai is required to use OpenAIModel. Install with: pip install 'farkad-ai[openai]'"
            )
        self._client = client
        self._resolver = model_resolver or (lambda tier: DEFAULT_OPENAI_MODELS[tier])

    def model_for(self, tier: ModelTier) -> str:
        return self._resolver(tier)

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        model = self.model_for(tier)
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
        messages = build_openai_messages(prompt)
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


def build_openai_messages(prompt: Prompt) -> list[dict[str, Any]]:
    system_message = {"role": "system", "content": prompt.instructions}
    user_parts: list[dict[str, Any]] = []
    if prompt.utterance:
        user_parts.append({"type": "text", "text": prompt.utterance})
    for blob in prompt.media:
        encoded = base64.b64encode(blob.data).decode("ascii")
        user_parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{blob.content_type.value};base64,{encoded}"},
            }
        )
    user_message = {"role": "user", "content": user_parts or [{"type": "text", "text": "Input."}]}
    return [system_message, user_message]


def extract_parsed_choice[T: BaseModel](
    schema: type[T], response: Any, *, tier: ModelTier, model: str
) -> T:
    choices = getattr(response, "choices", [])
    if not choices:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, "no choices in response"
        )
    message = choices[0].message
    if getattr(message, "refusal", None):
        raise ModelUnavailableError(
            tier, model, Unavailability.provider_refused, f"refusal: {message.refusal}"
        )
    parsed = getattr(message, "parsed", None)
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
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "no usage in response"
        )
    input_tokens = getattr(usage, "prompt_tokens", 0)
    output_tokens = getattr(usage, "completion_tokens", 0)
    return Usage(
        step=prompt.step,
        model=model,
        prompt_version=prompt.instructions_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        cost_cents=price_of(model).cost_cents(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_modality=modality_of(prompt),
        ),
    )
