from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from farkad_ai.models.anthropic import AnthropicModel
from farkad_ai.models.openai import OpenAIModel
from farkad_ai.models.port import ModelPort
from farkad_ai.models.recorded import RecordedModel
from farkad_ai.models.vertex import VertexModel


class ProviderName(StrEnum):
    vertex = "vertex"
    openai = "openai"
    anthropic = "anthropic"
    recorded = "recorded"


def create_model(provider: ProviderName, *, fixtures_dir: Path | None) -> ModelPort:
    match provider:
        case ProviderName.vertex:
            from google import genai

            return VertexModel(genai.Client(vertexai=True))
        case ProviderName.openai:
            from openai import AsyncOpenAI

            return OpenAIModel(AsyncOpenAI())
        case ProviderName.anthropic:
            from anthropic import AsyncAnthropic

            return AnthropicModel(AsyncAnthropic())
        case ProviderName.recorded:
            if fixtures_dir is None:
                raise ValueError("fixtures_dir is required for recorded provider")
            return RecordedModel(fixtures_dir)
