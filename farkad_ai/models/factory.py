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


def create_model(provider: ProviderName, *, fixtures_dir: Path) -> Model:
    match provider:
        case ProviderName.vertex:
            from farkad_ai.models.vertex import VertexModel

            return VertexModel.connected()
        case ProviderName.openai:
            from farkad_ai.models.openai import OpenAIModel

            return OpenAIModel.connected()
        case ProviderName.anthropic:
            from farkad_ai.models.anthropic import AnthropicModel

            return AnthropicModel.connected()
        case ProviderName.recorded:
            return RecordedModel(fixtures_dir)
