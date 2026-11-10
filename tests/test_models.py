from __future__ import annotations

import pytest

from farkad_ai.models.port import InputModality, MediaBlob, MediaType, PipelineStep, Prompt, Usage


@pytest.mark.parametrize(
    ("carried", "modality"),
    [
        ((), InputModality.text),
        ((MediaType.image_png,), InputModality.image),
        ((MediaType.image_jpeg, MediaType.audio_aac), InputModality.audio),
    ],
)
def test_a_calls_usage_says_what_it_carried(
    carried: tuple[MediaType, ...], modality: InputModality
) -> None:
    prompt = Prompt(
        step=PipelineStep.routing,
        instructions="Route",
        instructions_version="v1",
        media=tuple(MediaBlob(content_type=kind, data=b"") for kind in carried),
    )

    usage = Usage.answering(
        prompt, model="m", input_tokens=1, cached_input_tokens=0, output_tokens=1, latency_ms=1
    )

    assert usage.input_modality is modality
