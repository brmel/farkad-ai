from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from google import genai
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from farkad_ai.models.port import (
    ModelChoice,
    ModelTier,
    Prompt,
    Reasoning,
    TierChoices,
)
from farkad_ai.models.provider import PLACEHOLDER_INPUT, MissingCredentialsError, ProviderModel

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


class VertexModel(ProviderModel[genai.Client, types.GenerateContentResponse, APIError]):
    honoured_reasoning = THINKING_BUDGET
    refused_by = APIError
    default_choices: ClassVar[Mapping[ModelTier, ModelChoice]] = {
        ModelTier.fast: ModelChoice("gemini-3.5-flash-lite"),
        ModelTier.standard: ModelChoice("gemini-3.5-flash-lite", Reasoning.brief),
    }

    @classmethod
    def connected(
        cls,
        *,
        project: str | None = None,
        location: str | None = None,
        retries: Retries | None = None,
        choices: TierChoices | None = None,
    ) -> VertexModel:
        try:
            client = genai.Client(
                vertexai=True, project=project, location=location, http_options=_retrying(retries)
            )
        except (DefaultCredentialsError, ValueError) as error:
            raise MissingCredentialsError(
                "vertex", "GOOGLE_CLOUD_PROJECT set and `gcloud auth application-default login`"
            ) from error
        return cls(client, choices=choices)

    async def _send(
        self,
        prompt: Prompt,
        *,
        schema: type[BaseModel],
        tier: ModelTier,
        choice: ModelChoice,
    ) -> types.GenerateContentResponse:
        return await self._client.aio.models.generate_content(
            model=choice.model,
            contents=_parts(prompt),
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

    def _answer(
        self, response: types.GenerateContentResponse, *, tier: ModelTier, model: str
    ) -> object:
        return response.parsed

    def _tokens(self, response: types.GenerateContentResponse) -> tuple[int, int] | None:
        metadata = response.usage_metadata
        if (
            metadata is None
            or metadata.prompt_token_count is None
            or metadata.candidates_token_count is None
        ):
            return None
        # `thoughts_token_count` is absent, not zero, without thinking: https://googleapis.github.io/python-genai/
        thoughts = metadata.thoughts_token_count or 0
        return metadata.prompt_token_count, metadata.candidates_token_count + thoughts

    def _refusal(self, error: APIError) -> str:
        return f"{type(error).__name__} {error.code}"


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
