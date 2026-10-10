from __future__ import annotations

import base64
import time
from collections.abc import Mapping
from typing import Any

try:
    import anthropic  # type: ignore[import-not-found]
    from anthropic import APIError as AnthropicAPIError
    from anthropic import AsyncAnthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    AsyncAnthropic = Any
    AnthropicAPIError = Exception
    _ANTHROPIC_AVAILABLE = False

from pydantic import BaseModel, ValidationError

from farkad_ai.models.port import ModelChoice, ModelPort, TierChoices, fixed
from farkad_ai.types import (
    Completion,
    MediaBlob,
    MediaType,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Reasoning,
    Unavailability,
    Usage,
)

DEFAULT_ANTHROPIC_MODELS: Mapping[ModelTier, ModelChoice] = {
    ModelTier.fast: ModelChoice("claude-haiku-4-5-20251001"),
    ModelTier.standard: ModelChoice("claude-sonnet-5"),
}


class AnthropicModel(ModelPort):
    def __init__(
        self,
        client: AsyncAnthropic,
        *,
        choices: TierChoices | None = None,
    ) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "anthropic is required to use AnthropicModel. "
                "Install with: pip install 'farkad-ai[anthropic]'"
            )
        self._client = client
        self._choices = choices or fixed(DEFAULT_ANTHROPIC_MODELS)

    async def model_for(self, tier: ModelTier) -> str:
        choice = await self._choices(tier)
        if choice.reasoning is not Reasoning.none:
            raise ModelUnavailableError(
                tier,
                choice.model,
                Unavailability.unsupported_request,
                f"reasoning {choice.reasoning} with a forced structured answer",
            )
        return choice.model

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        model = await self.model_for(tier)
        started = time.monotonic()
        response = await self._send(prompt, schema=schema, model=model, tier=tier)
        latency_ms = int((time.monotonic() - started) * 1000)
        value = extract_tool_result(schema, response, tier=tier, model=model)
        return Completion(
            value=value,
            usage=usage_from_anthropic(
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
        tool_name = schema.__name__
        tools = [
            {
                "name": tool_name,
                "description": f"Output schema for {tool_name}",
                "input_schema": schema.model_json_schema(),
            }
        ]
        messages = build_anthropic_messages(prompt, tier=tier, model=model)
        try:
            return await self._client.messages.create(
                model=model,
                max_tokens=4096,
                system=prompt.instructions,
                messages=messages,
                tools=tools,
                tool_choice={"type": "tool", "name": tool_name},
            )
        except AnthropicAPIError as error:
            raise ModelUnavailableError(
                tier,
                model,
                Unavailability.provider_refused,
                str(error),
            ) from error


def build_anthropic_messages(
    prompt: Prompt, *, tier: ModelTier, model: str
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    if prompt.utterance:
        content.append({"type": "text", "text": prompt.utterance})
    content.extend(image_block(blob, tier=tier, model=model) for blob in prompt.media)
    return [{"role": "user", "content": content or [{"type": "text", "text": "Process input."}]}]


def image_block(blob: MediaBlob, *, tier: ModelTier, model: str) -> dict[str, Any]:
    match blob.content_type:
        case MediaType.image_jpeg | MediaType.image_png:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": blob.content_type.value,
                    "data": base64.b64encode(blob.data).decode("ascii"),
                },
            }
        case MediaType.audio_aac:
            raise ModelUnavailableError(
                tier, model, Unavailability.provider_refused, "audio input unsupported"
            )


def extract_tool_result[T: BaseModel](
    schema: type[T], response: Any, *, tier: ModelTier, model: str
) -> T:
    tool_blocks = [block for block in response.content if block.type == "tool_use"]
    if not tool_blocks:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, "no tool_use block in response"
        )
    try:
        return schema.model_validate(tool_blocks[0].input)
    except ValidationError as error:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, schema.__name__
        ) from error


def usage_from_anthropic(
    response: Any,
    *,
    prompt: Prompt,
    tier: ModelTier,
    model: str,
    latency_ms: int,
) -> Usage:
    if response.usage is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "no usage object in response"
        )
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return Usage.answering(
        prompt,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
