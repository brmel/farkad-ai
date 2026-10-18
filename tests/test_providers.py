from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

pytest.importorskip("anthropic")
pytest.importorskip("openai")
pytest.importorskip("google.genai")

from google.genai import types

from farkad_ai.models.anthropic import AnthropicModel
from farkad_ai.models.openai import OpenAIModel
from farkad_ai.models.port import (
    ModelChoice,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Reasoning,
    Unavailability,
    Usage,
    fixed,
)
from farkad_ai.models.vertex import usage_of


class HealthFact(BaseModel):
    category: str
    amount: int


@pytest.mark.anyio
async def test_an_anthropic_tool_answer_is_parsed_and_counted() -> None:
    client = Mock()
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = {"category": "hydration", "amount": 250}

    mock_response = Mock()
    mock_response.content = [mock_tool_block]
    mock_response.usage = Mock()
    mock_response.usage.input_tokens = 40
    mock_response.usage.output_tokens = 15

    client.messages = Mock()
    client.messages.create = AsyncMock(return_value=mock_response)

    prompt = Prompt(
        step=PipelineStep.routing,
        instructions="Extract facts",
        instructions_version="v1",
        utterance="Had 250ml",
    )
    completion = await AnthropicModel(client).complete(
        prompt, schema=HealthFact, tier=ModelTier.fast
    )

    assert completion.value.category == "hydration"
    assert completion.value.amount == 250
    assert completion.usage.input_tokens == 40
    assert completion.usage.output_tokens == 15
    assert client.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5-20251001"


@pytest.mark.anyio
async def test_an_openai_structured_answer_is_parsed_and_counted() -> None:
    client = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.refusal = None
    mock_choice.message.parsed = {"category": "sleep", "amount": 8}

    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 20

    client.beta = Mock()
    client.beta.chat = Mock()
    client.beta.chat.completions = Mock()
    client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

    prompt = Prompt(
        step=PipelineStep.extraction,
        instructions="Extract sleep",
        instructions_version="v1",
        utterance="Slept 8 hours",
    )
    completion = await OpenAIModel(client).complete(
        prompt, schema=HealthFact, tier=ModelTier.standard
    )

    assert completion.value.category == "sleep"
    assert completion.value.amount == 8
    assert completion.usage.input_tokens == 50
    assert completion.usage.output_tokens == 20
    assert client.beta.chat.completions.parse.call_args.kwargs["model"] == "gpt-4o"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter", [AnthropicModel, OpenAIModel])
async def test_a_reasoning_level_the_adapter_cannot_honour_is_refused_not_ignored(
    adapter: type[AnthropicModel] | type[OpenAIModel],
) -> None:
    thinking = fixed({ModelTier.standard: ModelChoice("some-model", Reasoning.brief)})
    model = adapter(Mock(), choices=thinking)
    asked = Prompt(step=PipelineStep.extraction, instructions="Extract", instructions_version="v1")

    with pytest.raises(ModelUnavailableError) as refused:
        await model.complete(asked, schema=HealthFact, tier=ModelTier.standard)

    assert refused.value.because is Unavailability.unsupported_request


def counted(*, prompt: int | None, candidates: int | None) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt, candidates_token_count=candidates
        )
    )


def vertex_usage(response: types.GenerateContentResponse) -> Usage:
    asked = Prompt(step=PipelineStep.routing, instructions="Route", instructions_version="v1")
    return usage_of(
        response, prompt=asked, tier=ModelTier.fast, model="gemini-3.5-flash-lite", latency_ms=1
    )


@pytest.mark.parametrize(
    "response",
    [
        types.GenerateContentResponse(),
        counted(prompt=None, candidates=800),
        counted(prompt=9_000, candidates=None),
    ],
    ids=["no usage", "no input count", "no output count"],
)
def test_a_vertex_answer_that_does_not_count_its_tokens_is_refused(
    response: types.GenerateContentResponse,
) -> None:
    with pytest.raises(ModelUnavailableError) as refused:
        vertex_usage(response)

    assert refused.value.because is Unavailability.usage_not_reported


def test_a_counted_vertex_answer_reports_its_tokens() -> None:
    usage = vertex_usage(counted(prompt=9_000, candidates=800))

    assert (usage.input_tokens, usage.output_tokens) == (9_000, 800)
