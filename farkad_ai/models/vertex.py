from __future__ import annotations

import time
from collections.abc import Callable, Mapping

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError

    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    APIError = Exception  # type: ignore[assignment,misc]
    _GENAI_AVAILABLE = False

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

DEFAULT_MODELS: Mapping[ModelTier, str] = {
    ModelTier.fast: "gemini-2.5-flash-lite",
    ModelTier.standard: "gemini-2.5-flash",
}

DEFAULT_THINKING: Mapping[ModelTier, int] = {
    ModelTier.fast: 0,
    ModelTier.standard: 0,
}


class VertexModel(ModelPort):
    def __init__(
        self,
        client: genai.Client,
        *,
        model_resolver: Callable[[ModelTier], str] | None = None,
        thinking_budget: Callable[[ModelTier], int] | None = None,
    ) -> None:
        if not _GENAI_AVAILABLE:
            raise RuntimeError(
                "google-genai is required to use VertexModel. "
                "Install with: pip install 'farkad-ai[google]'"
            )
        self._client = client
        self._resolver = model_resolver or (lambda tier: DEFAULT_MODELS[tier])
        self._thinking = thinking_budget or (lambda tier: DEFAULT_THINKING.get(tier, 0))

    def model_for(self, tier: ModelTier) -> str:
        return self._resolver(tier)

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        model = self.model_for(tier)
        started = time.monotonic()
        response = await self._answered(prompt, schema=schema, tier=tier, model=model)
        latency_ms = int((time.monotonic() - started) * 1000)
        value = parsed_as(schema, response, tier=tier, model=model)
        return Completion(
            value=value,
            usage=usage_of(response, prompt=prompt, tier=tier, model=model, latency_ms=latency_ms),
        )

    async def _answered(
        self,
        prompt: Prompt,
        *,
        schema: type[BaseModel],
        tier: ModelTier,
        model: str,
    ) -> types.GenerateContentResponse:
        try:
            return await self._client.aio.models.generate_content(
                model=model,
                contents=parts(prompt),
                config=types.GenerateContentConfig(
                    system_instruction=prompt.instructions,
                    response_mime_type="application/json",
                    response_schema=schema,
                    thinking_config=types.ThinkingConfig(thinking_budget=self._thinking(tier)),
                ),
            )
        except APIError as error:
            raise ModelUnavailableError(
                tier,
                model,
                Unavailability.provider_refused,
                f"{type(error).__name__} {error.code}",
            ) from error


def parsed_as[T: BaseModel](
    schema: type[T],
    response: types.GenerateContentResponse,
    *,
    tier: ModelTier,
    model: str,
) -> T:
    try:
        return schema.model_validate(response.parsed)
    except ValidationError as error:
        raise ModelUnavailableError(
            tier, model, Unavailability.output_did_not_parse, schema.__name__
        ) from error


def parts(prompt: Prompt) -> types.ContentListUnion:
    spoken = [types.Part.from_text(text=prompt.utterance)] if prompt.utterance else []
    sent: list[types.PartUnion] = [
        *spoken,
        *(
            types.Part.from_bytes(data=blob.data, mime_type=blob.content_type)
            for blob in prompt.media
        ),
    ]
    if not sent:
        sent.append(types.Part.from_text(text="Input."))
    return sent


def usage_of(
    response: types.GenerateContentResponse,
    *,
    prompt: Prompt,
    tier: ModelTier,
    model: str,
    latency_ms: int,
) -> Usage:
    metadata = response.usage_metadata
    if metadata is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "no usage metadata on the response"
        )
    if metadata.prompt_token_count is None or metadata.candidates_token_count is None:
        raise ModelUnavailableError(
            tier, model, Unavailability.usage_not_reported, "the response counted no tokens"
        )
    input_tokens = metadata.prompt_token_count
    output_tokens = metadata.candidates_token_count + (metadata.thoughts_token_count or 0)
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
