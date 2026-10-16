from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

pytest.importorskip("anthropic")
pytest.importorskip("openai")

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
    fixed,
)


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
