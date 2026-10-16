from __future__ import annotations

from pathlib import Path

import pytest

from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.port import InputModality, MediaBlob, MediaType, PipelineStep, Prompt, Usage
from farkad_ai.models.recorded import RecordedModel


def test_the_recorded_provider_replays_from_the_directory_given(tmp_path: Path) -> None:
    model = create_model(ProviderName.recorded, fixtures_dir=tmp_path)
    assert isinstance(model, RecordedModel)


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

    usage = Usage.answering(prompt, model="m", input_tokens=1, output_tokens=1, latency_ms=1)

    assert usage.input_modality is modality
