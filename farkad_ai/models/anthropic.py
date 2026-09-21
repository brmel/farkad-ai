from __future__ import annotations

import base64
import time
from collections.abc import Callable, Mapping
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

DEFAULT_ANTHROPIC_MODELS: Mapping[ModelTier, str] = {
    ModelTier.fast: "claude-3-5-haiku-20241022",
    ModelTier.standard: "claude-3-5-sonnet-20241022",
}


class AnthropicModel(ModelPort):
    def __init__(
        self,
        client: AsyncAnthropic,
        *,
        model_resolver: Callable[[ModelTier], str] | None = None,
    ) -> None:
        if not _ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "anthropic is required to use AnthropicModel. "
                "Install with: pip install 'farkad-ai[anthropic]'"
            )
        self._client = client
        self._resolver = model_resolver or (lambda tier: DEFAULT_ANTHROPIC_MODELS[tier])

    def model_for(self, tier: ModelTier) -> str:
        return self._resolver(tier)

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        model = self.model_for(tier)
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
        messages = build_anthropic_messages(prompt)
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


def build_anthropic_messages(prompt: Prompt) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    if prompt.utterance:
        content.append({"type": "text", "text": prompt.utterance})
    for blob in prompt.media:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": blob.content_type.value,
                    "data": base64.b64encode(blob.data).decode("ascii"),
                },
            }
        )
    return [{"role": "user", "content": content or [{"type": "text", "text": "Process input."}]}]


def extract_tool_result[T: BaseModel](
    schema: type[T], response: Any, *, tier: ModelTier, model: str
) -> T:
    tool_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
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
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "no usage object in response"
        )
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
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
