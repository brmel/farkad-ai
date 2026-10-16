from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from farkad_ai.models.port import Model
from farkad_ai.models.recorded import RecordedModel


class ProviderName(StrEnum):
    vertex = "vertex"
    openai = "openai"
    anthropic = "anthropic"
    recorded = "recorded"


class MissingCredentialsError(Exception):
    def __init__(self, provider: ProviderName, remedy: str) -> None:
        super().__init__(f"the {provider} provider needs {remedy}")


def create_model(provider: ProviderName, *, fixtures_dir: Path) -> Model:
    match provider:
        case ProviderName.vertex:
            from google import genai
            from google.auth.exceptions import DefaultCredentialsError

            from farkad_ai.models.vertex import VertexModel

            try:
                return VertexModel(genai.Client(vertexai=True))
            except (DefaultCredentialsError, ValueError) as error:
                raise MissingCredentialsError(
                    provider,
                    "GOOGLE_CLOUD_PROJECT set and `gcloud auth application-default login`",
                ) from error
        case ProviderName.openai:
            from openai import AsyncOpenAI, OpenAIError

            from farkad_ai.models.openai import OpenAIModel

            try:
                return OpenAIModel(AsyncOpenAI())
            except OpenAIError as error:
                raise MissingCredentialsError(provider, "OPENAI_API_KEY set") from error
        case ProviderName.anthropic:
            from anthropic import AsyncAnthropic

            from farkad_ai.models.anthropic import AnthropicModel

            client = AsyncAnthropic()
            if client.api_key is None and client.auth_token is None and client.credentials is None:
                raise MissingCredentialsError(provider, "ANTHROPIC_API_KEY set")
            return AnthropicModel(client)
        case ProviderName.recorded:
            return RecordedModel(fixtures_dir)
