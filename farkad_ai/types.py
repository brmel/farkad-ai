from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PipelineStep(StrEnum):
    routing = "routing"
    extraction = "extraction"
    recompute = "recompute"
    demo = "demo"
    vision = "vision"


class ModelTier(StrEnum):
    fast = "fast"
    standard = "standard"


class MediaType(StrEnum):
    audio_aac = "audio/aac"
    image_jpeg = "image/jpeg"
    image_png = "image/png"


@dataclass(frozen=True, slots=True)
class MediaBlob:
    content_type: MediaType
    data: bytes


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: PipelineStep
    model: str
    prompt_version: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    cost_cents: Decimal = Field(ge=0)


@dataclass(frozen=True, slots=True)
class Prompt:
    step: PipelineStep
    instructions: str
    instructions_version: str
    utterance: str = ""
    media: tuple[MediaBlob, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Completion[T: BaseModel]:
    value: T
    usage: Usage


class Unavailability(StrEnum):
    provider_refused = "provider_refused"
    output_did_not_parse = "output_did_not_parse"
    usage_not_reported = "usage_not_reported"


class ModelUnavailableError(Exception):
    def __init__(self, tier: ModelTier, model: str, because: Unavailability, detail: str) -> None:
        super().__init__(f"{tier} model {model} unavailable: {because} ({detail})")
        self.tier = tier
        self.model = model
        self.because = because
