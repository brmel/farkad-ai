from __future__ import annotations

import pytest
from pydantic import BaseModel

from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import ExtractionContext
from farkad_ai.models.port import (
    Completion,
    Model,
    ModelTier,
    ModelUnavailableError,
    Prompt,
    Unavailability,
)
from tests.support import Tracked, a_usage

TWO_EGGS = ExtractionContext(pillar=Tracked("food"), transcript="two eggs", mentions=("two eggs",))


class TierScript(Model):
    def __init__(self, **answers: str | Unavailability) -> None:
        self._answers = answers
        self.asked: list[ModelTier] = []

    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        self.asked.append(tier)
        match self._answers[tier.value]:
            case Unavailability() as because:
                raise ModelUnavailableError(tier, f"model-{tier}", because, "detail")
            case item:
                answer = {"entries": [{"pillar": "food", "item": item}]}
                return Completion(value=schema.model_validate(answer), usage=a_usage(prompt.step))


async def escalated(script: TierScript) -> str:
    result = await PillarExtractor(script).extract_escalating(TWO_EGGS)
    return str(result.entries[0].values["item"])


@pytest.mark.anyio
async def test_the_fast_tier_answers_when_it_can() -> None:
    script = TierScript(fast="fast", standard="standard")

    assert await escalated(script) == "fast"
    assert script.asked == [ModelTier.fast]


@pytest.mark.anyio
async def test_an_answer_that_did_not_parse_escalates_to_standard() -> None:
    script = TierScript(fast=Unavailability.output_did_not_parse, standard="standard")

    assert await escalated(script) == "standard"
    assert script.asked == [ModelTier.fast, ModelTier.standard]


@pytest.mark.anyio
async def test_a_refusal_neither_tier_can_answer_is_never_paid_for_twice() -> None:
    for because in (
        Unavailability.provider_refused,
        Unavailability.unsupported_request,
        Unavailability.usage_not_reported,
    ):
        script = TierScript(fast=because, standard="standard")

        with pytest.raises(ModelUnavailableError):
            await escalated(script)
        assert script.asked == [ModelTier.fast]


@pytest.mark.anyio
async def test_both_tiers_unparsed_is_a_refusal() -> None:
    script = TierScript(
        fast=Unavailability.output_did_not_parse, standard=Unavailability.output_did_not_parse
    )

    with pytest.raises(ModelUnavailableError):
        await escalated(script)
    assert script.asked == [ModelTier.fast, ModelTier.standard]
