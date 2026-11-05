from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from farkad_ai.models.port import Model
from farkad_ai.models.recorded import RecordedModel


class MissingCredentialsError(Exception):
    def __init__(self, provider: str, remedy: str) -> None:
        super().__init__(f"the {provider} provider needs {remedy}")


class ProviderName(StrEnum):
    vertex = "vertex"
    recorded = "recorded"


def create_model(provider: ProviderName, *, fixtures_dir: Path) -> Model:
    match provider:
        case ProviderName.vertex:
            from farkad_ai.models.vertex import VertexModel

            return VertexModel.connected()
        case ProviderName.recorded:
            return RecordedModel(fixtures_dir)
