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


class InputModality(StrEnum):
    """What a call carried, because a provider bills audio input at its own rate."""

    text = "text"
    audio = "audio"
    image = "image"


class MediaType(StrEnum):
    audio_aac = "audio/aac"
    image_jpeg = "image/jpeg"
    image_png = "image/png"

    @property
    def modality(self) -> InputModality:
        match self:
            case MediaType.audio_aac:
                return InputModality.audio
            case MediaType.image_jpeg | MediaType.image_png:
                return InputModality.image


@dataclass(frozen=True, slots=True)
class MediaBlob:
    content_type: MediaType
    data: bytes


class Usage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    step: PipelineStep
    model: str
    prompt_version: str
    input_modality: InputModality
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)

    @classmethod
    def answering(
        cls, prompt: Prompt, *, model: str, input_tokens: int, output_tokens: int, latency_ms: int
    ) -> Usage:
        return cls(
            step=prompt.step,
            model=model,
            prompt_version=prompt.instructions_version,
            input_modality=prompt.input_modality,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )


@dataclass(frozen=True, slots=True)
class Prompt:
    """`instructions_version` names the asset the instructions came from, not the rendered text."""

    step: PipelineStep
    instructions: str
    instructions_version: str
    utterance: str = ""
    media: tuple[MediaBlob, ...] = field(default_factory=tuple)

    @property
    def input_modality(self) -> InputModality:
        """Any audio makes it an audio call, whose input tokens are the dearer ones."""
        carried = {blob.content_type.modality for blob in self.media}
        if InputModality.audio in carried:
            return InputModality.audio
        return InputModality.image if carried else InputModality.text


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
