from __future__ import annotations

import os
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from farkad_ai.models.anthropic import AnthropicModel
from farkad_ai.models.openai import OpenAIModel
from farkad_ai.models.port import ModelPort
from farkad_ai.models.recorded import RecordedModel
from farkad_ai.models.vertex import VertexModel
from farkad_ai.types import ModelTier


class ProviderName(StrEnum):
    vertex = "vertex"
    gemini = "gemini"
    openai = "openai"
    anthropic = "anthropic"
    recorded = "recorded"


def _build_vertex(
    *,
    project: str | None,
    location: str | None,
    model_resolver: Callable[[ModelTier], str] | None,
) -> ModelPort:
    from google import genai

    resolved_project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
    resolved_location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    client = genai.Client(vertexai=True, project=resolved_project, location=resolved_location)
    return VertexModel(client, model_resolver=model_resolver)


def _build_openai(
    *,
    api_key: str | None,
    model_resolver: Callable[[ModelTier], str] | None,
) -> ModelPort:
    from openai import AsyncOpenAI  # type: ignore[import-not-found]

    client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    return OpenAIModel(client, model_resolver=model_resolver)


def _build_anthropic(
    *,
    api_key: str | None,
    model_resolver: Callable[[ModelTier], str] | None,
) -> ModelPort:
    from anthropic import AsyncAnthropic  # type: ignore[import-not-found]

    client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    return AnthropicModel(client, model_resolver=model_resolver)


def _build_raw_model(
    provider: ProviderName,
    *,
    api_key: str | None,
    project: str | None,
    location: str | None,
    fixtures_dir: Path | None,
    model_resolver: Callable[[ModelTier], str] | None,
) -> ModelPort:
    match provider:
        case ProviderName.vertex | ProviderName.gemini:
            return _build_vertex(project=project, location=location, model_resolver=model_resolver)
        case ProviderName.openai:
            return _build_openai(api_key=api_key, model_resolver=model_resolver)
        case ProviderName.anthropic:
            return _build_anthropic(api_key=api_key, model_resolver=model_resolver)
        case ProviderName.recorded:
            if fixtures_dir is None:
                raise ValueError("fixtures_dir is required for recorded provider")
            return RecordedModel(fixtures_dir)


def create_model(
    provider: ProviderName | str = ProviderName.vertex,
    *,
    api_key: str | None = None,
    project: str | None = None,
    location: str | None = None,
    fixtures_dir: Path | None = None,
    model_resolver: Callable[[ModelTier], str] | None = None,
) -> ModelPort:
    resolved_provider = ProviderName(provider)
    return _build_raw_model(
        resolved_provider,
        api_key=api_key,
        project=project,
        location=location,
        fixtures_dir=fixtures_dir,
        model_resolver=model_resolver,
    )
