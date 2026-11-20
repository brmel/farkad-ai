from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from farkad_ai.models.port import (
    Model,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
)
from farkad_ai.models.recorded import RecordedModel
from farkad_ai.models.recording import RecordedUsage, Recording, fingerprint

PROMPT = Prompt(PipelineStep.routing, "Say what was eaten", "v1", utterance="lunch")


class Said(BaseModel):
    said: str


type Adapter = Callable[[dict[str, object]], Model]


def recorded(tmp_path: Path) -> Adapter:
    def adapter(answer: dict[str, object]) -> Model:
        recording = Recording(
            tier=ModelTier.fast,
            schema="Said",
            instructions=PROMPT.instructions,
            utterance=PROMPT.utterance,
            value=answer,
            usage=RecordedUsage(
                model="recorded",
                input_tokens=1,
                cached_input_tokens=0,
                output_tokens=1,
                latency_ms=1,
            ),
        )
        key = fingerprint(PROMPT, schema=Said, tier=ModelTier.fast)
        (tmp_path / f"{key}.json").write_text(recording.written())
        return RecordedModel(tmp_path)

    return adapter


def vertex(tmp_path: Path) -> Adapter:
    pytest.importorskip("google.genai")
    from farkad_ai.models.vertex import VertexModel

    def adapter(answer: dict[str, object]) -> Model:
        client = Mock()
        client.aio.models.generate_content = AsyncMock(
            return_value=Mock(
                parsed=answer,
                usage_metadata=Mock(
                    prompt_token_count=1,
                    candidates_token_count=1,
                    cached_content_token_count=None,
                    thoughts_token_count=None,
                ),
            )
        )
        return VertexModel(client)

    return adapter


@pytest.fixture(params=[recorded, vertex], ids=["recorded", "vertex"])
def adapter(request: pytest.FixtureRequest, tmp_path: Path) -> Adapter:
    make: Callable[[Path], Adapter] = request.param
    return make(tmp_path)


@pytest.mark.anyio
async def test_an_adapter_answers_a_prompt_with_the_parsed_schema_and_the_calls_usage(
    adapter: Adapter,
) -> None:
    completion = await adapter({"said": "a meal"}).complete(
        PROMPT, schema=Said, tier=ModelTier.fast
    )

    assert completion.value == Said(said="a meal")
    assert completion.usage.step == PipelineStep.routing
    assert completion.usage.prompt_version == "v1"


@pytest.mark.anyio
async def test_an_adapter_refuses_an_answer_that_does_not_fit_the_schema_with_a_typed_error(
    adapter: Adapter,
) -> None:
    with pytest.raises(ModelUnavailableError) as refused:
        await adapter({"said": 1}).complete(PROMPT, schema=Said, tier=ModelTier.fast)

    assert refused.value.because is Unavailability.output_did_not_parse
