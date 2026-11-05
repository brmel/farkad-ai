from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

pytest.importorskip("google.genai")

from google.genai import types

from farkad_ai.models.port import (
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
    Usage,
)
from farkad_ai.models.vertex import VertexModel


class HealthFact(BaseModel):
    category: str
    amount: int


def answered(metadata: types.GenerateContentResponseUsageMetadata | None) -> Mock:
    return Mock(parsed={"category": "water", "amount": 250}, usage_metadata=metadata)


def counted(*, prompt: int | None, candidates: int | None) -> Mock:
    return answered(
        types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt, candidates_token_count=candidates
        )
    )


async def vertex_usage(response: Mock) -> Usage:
    client = Mock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    asked = Prompt(step=PipelineStep.routing, instructions="Route", instructions_version="v1")
    completion = await VertexModel(client).complete(asked, schema=HealthFact, tier=ModelTier.fast)
    return completion.usage


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [
        answered(None),
        counted(prompt=None, candidates=800),
        counted(prompt=9_000, candidates=None),
    ],
    ids=["no usage", "no input count", "no output count"],
)
async def test_a_vertex_answer_that_does_not_count_its_tokens_is_refused(
    response: Mock,
) -> None:
    with pytest.raises(ModelUnavailableError) as refused:
        await vertex_usage(response)

    assert refused.value.because is Unavailability.usage_not_reported


@pytest.mark.anyio
async def test_a_counted_vertex_answer_reports_its_tokens() -> None:
    usage = await vertex_usage(counted(prompt=9_000, candidates=800))

    assert (usage.input_tokens, usage.output_tokens) == (9_000, 800)
