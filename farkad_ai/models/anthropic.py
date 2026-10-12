from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal

try:
    from anthropic import APIError as AnthropicAPIError
    from anthropic import AsyncAnthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    AsyncAnthropic = Any  # type: ignore[assignment,misc]
    AnthropicAPIError = Exception  # type: ignore[assignment,misc]
    _ANTHROPIC_AVAILABLE = False

if TYPE_CHECKING:
    from anthropic.types import ImageBlockParam, MessageParam, TextBlockParam, ToolParam

from pydantic import BaseModel

from farkad_ai.models.port import ModelChoice, TierChoices, fixed
from farkad_ai.models.provider import ProviderModel
from farkad_ai.types import (
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


class AnthropicModel(ProviderModel):
    honoured_reasoning = (Reasoning.none,)

    def __init__(
        self,
        client: AsyncAnthropic,
        *,
        choices: TierChoices | None = None,
    ) -> None:
        super().__init__(
            sdk_installed=_ANTHROPIC_AVAILABLE,
            sdk="anthropic",
            extra="anthropic",
            choices=choices or fixed(DEFAULT_ANTHROPIC_MODELS),
        )
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
        tool_name = schema.__name__
        tools: list[ToolParam] = [
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

    def _answer(self, response: Any, *, tier: ModelTier, model: str) -> object:
        tool_blocks = [block for block in response.content if block.type == "tool_use"]
        if not tool_blocks:
            raise ModelUnavailableError(
                tier, model, Unavailability.output_did_not_parse, "no tool_use block in response"
            )
        return tool_blocks[0].input

    def _usage(
        self, response: Any, *, prompt: Prompt, tier: ModelTier, model: str, latency_ms: int
    ) -> Usage:
        if response.usage is None:
            raise ModelUnavailableError(
                tier, model, Unavailability.usage_not_reported, "no usage object in response"
            )
        return Usage.answering(
            prompt,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
        )


def build_anthropic_messages(prompt: Prompt, *, tier: ModelTier, model: str) -> list[MessageParam]:
    content: list[TextBlockParam | ImageBlockParam] = []
    if prompt.utterance:
        content.append({"type": "text", "text": prompt.utterance})
    content.extend(image_block(blob, tier=tier, model=model) for blob in prompt.media)
    return [{"role": "user", "content": content or [{"type": "text", "text": "Process input."}]}]


def image_block(blob: MediaBlob, *, tier: ModelTier, model: str) -> ImageBlockParam:
    match blob.content_type:
        case MediaType.image_jpeg:
            return base64_image("image/jpeg", blob.data)
        case MediaType.image_png:
            return base64_image("image/png", blob.data)
        case MediaType.audio_aac:
            raise ModelUnavailableError(
                tier, model, Unavailability.provider_refused, "audio input unsupported"
            )


def base64_image(media_type: Literal["image/jpeg", "image/png"], data: bytes) -> ImageBlockParam:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(data).decode("ascii"),
        },
    }
