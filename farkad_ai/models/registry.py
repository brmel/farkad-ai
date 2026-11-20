from __future__ import annotations

from enum import StrEnum

from farkad_ai.eval.example import RECORDINGS
from farkad_ai.models.port import Model
from farkad_ai.models.recorded import RecordedModel


class ProviderName(StrEnum):
    vertex = "vertex"
    recorded = "recorded"


def connect(provider: ProviderName) -> Model:
    match provider:
        case ProviderName.vertex:
            from farkad_ai.models.vertex import VertexModel

            return VertexModel.connected()
        case ProviderName.recorded:
            return RecordedModel(RECORDINGS)
