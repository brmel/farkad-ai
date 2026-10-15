from __future__ import annotations

from collections.abc import Mapping

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

from pydantic import BaseModel

from farkad_ai.models.port import (
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
from farkad_ai.models.provider import ProviderModel

# Gemini's thinking budget in tokens: https://ai.google.dev/gemini-api/docs/thinking
THINKING_BUDGET: Mapping[Reasoning, int] = {
    Reasoning.none: 0,
    Reasoning.brief: 512,
    Reasoning.thorough: 2048,
}

DEFAULT_CHOICES: Mapping[ModelTier, ModelChoice] = {
    ModelTier.fast: ModelChoice("gemini-3.5-flash-lite"),
    ModelTier.standard: ModelChoice("gemini-3.5-flash-lite", Reasoning.brief),
}


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
    # `thoughts_token_count` is absent, not zero, without thinking: https://googleapis.github.io/python-genai/
    output_tokens = metadata.candidates_token_count + (metadata.thoughts_token_count or 0)
    return Usage.answering(
        prompt,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )


class VertexModel(ProviderModel):
    honoured_reasoning = THINKING_BUDGET

    def __init__(
        self,
        client: genai.Client,
        *,
        choices: TierChoices | None = None,
    ) -> None:
        super().__init__(
            sdk_installed=_GENAI_AVAILABLE,
            sdk="google-genai",
            extra="google",
            choices=choices or fixed(DEFAULT_CHOICES),
        )
        self._client = client

    async def _send(
        self,
        prompt: Prompt,
        *,
        schema: type[BaseModel],
        tier: ModelTier,
        choice: ModelChoice,
    ) -> types.GenerateContentResponse:
        model = choice.model
        try:
            return await self._client.aio.models.generate_content(
                model=model,
                contents=parts(prompt),
                config=types.GenerateContentConfig(
                    system_instruction=prompt.instructions,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    response_mime_type="application/json",
                    response_schema=schema,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=THINKING_BUDGET[choice.reasoning]
                    ),
                ),
            )
        except APIError as error:
            raise ModelUnavailableError(
                tier,
                model,
                Unavailability.provider_refused,
                f"{type(error).__name__} {error.code}",
            ) from error

    def _answer(
        self, response: types.GenerateContentResponse, *, tier: ModelTier, model: str
    ) -> object:
        return response.parsed

    _usage = staticmethod(usage_of)


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
