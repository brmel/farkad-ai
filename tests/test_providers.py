from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from farkad_ai.models.anthropic import AnthropicModel
from farkad_ai.models.openai import OpenAIModel
from farkad_ai.types import (
    InputModality,
    MediaBlob,
    MediaType,
    ModelTier,
    PipelineStep,
    Prompt,
    Usage,
)


class HealthFact(BaseModel):
    category: str
    amount: int


def test_missing_anthropic_dependency_raises_clear_error() -> None:
    with (
        patch("farkad_ai.models.anthropic._ANTHROPIC_AVAILABLE", False),
        pytest.raises(RuntimeError, match="anthropic is required"),
    ):
        AnthropicModel(Mock())


def test_missing_openai_dependency_raises_clear_error() -> None:
    with (
        patch("farkad_ai.models.openai._OPENAI_AVAILABLE", False),
        pytest.raises(RuntimeError, match="openai is required"),
    ):
        OpenAIModel(Mock())


@pytest.mark.anyio
async def test_anthropic_model_parses_tool_response() -> None:
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

    with patch("farkad_ai.models.anthropic._ANTHROPIC_AVAILABLE", True):
        adapter = AnthropicModel(client)
        assert await adapter.model_for(ModelTier.fast) == "claude-haiku-4-5-20251001"

        prompt = Prompt(
            step=PipelineStep.routing,
            instructions="Extract facts",
            instructions_version="v1",
            utterance="Had 250ml",
        )
        completion = await adapter.complete(prompt, schema=HealthFact, tier=ModelTier.fast)

        assert completion.value.category == "hydration"
        assert completion.value.amount == 250
        assert completion.usage.input_tokens == 40
        assert completion.usage.output_tokens == 15


@pytest.mark.anyio
async def test_openai_model_parses_structured_response() -> None:
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

    with patch("farkad_ai.models.openai._OPENAI_AVAILABLE", True):
        adapter = OpenAIModel(client)
        assert await adapter.model_for(ModelTier.standard) == "gpt-4o"

        prompt = Prompt(
            step=PipelineStep.extraction,
            instructions="Extract sleep",
            instructions_version="v1",
            utterance="Slept 8 hours",
        )
        completion = await adapter.complete(prompt, schema=HealthFact, tier=ModelTier.standard)

        assert completion.value.category == "sleep"
        assert completion.value.amount == 8
        assert completion.usage.input_tokens == 50
        assert completion.usage.output_tokens == 20


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
