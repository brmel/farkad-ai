from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PipelineStep(StrEnum):
    """Pipeline stage for a model call, stored on captures and dashboards."""

    routing = "routing"
    extraction = "extraction"
    recompute = "recompute"
    demo = "demo"
    vision = "vision"
    memory = "memory"


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
    model_config = ConfigDict(extra="forbid", frozen=True)

    step: PipelineStep
    model: str
    prompt_version: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


@dataclass(frozen=True, slots=True)
class Prompt:
    """`instructions_version` names the asset the instructions came from, not the rendered text."""

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
    """A refusal passes with a retry; an unparseable or unpriced answer does not."""

    provider_refused = "provider_refused"
    output_did_not_parse = "output_did_not_parse"
    usage_not_reported = "usage_not_reported"


class ModelUnavailableError(Exception):
    """Carries no prompt and no transcript, which a log would then hold."""

    def __init__(self, tier: ModelTier, model: str, because: Unavailability, detail: str) -> None:
        super().__init__(f"{tier} model {model} unavailable: {because} ({detail})")
        self.tier = tier
        self.model = model
        self.because = because
