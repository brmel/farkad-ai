from __future__ import annotations

import pytest

from farkad_ai.extraction.adaptive import AdaptiveExtractor
from farkad_ai.extraction.port import (
    ExtractedEntry,
    ExtractionContext,
    ExtractionResult,
    TieredExtractionPort,
)
from farkad_ai.types import ModelTier, ModelUnavailableError, PipelineStep, Unavailability
from tests.support import PillarConfig, a_usage

TWO_EGGS = ExtractionContext(
    config=PillarConfig("food"), transcript="two eggs", mentions=("two eggs",)
)


class TierScript(TieredExtractionPort[PillarConfig]):
    def __init__(self, **answers: str | Unavailability) -> None:
        self._answers = answers
        self.asked: list[ModelTier] = []

    async def extract(
        self, context: ExtractionContext[PillarConfig], *, tier: ModelTier
    ) -> ExtractionResult:
        self.asked.append(tier)
        match self._answers[tier.value]:
            case Unavailability() as because:
                raise ModelUnavailableError(tier, f"model-{tier}", because, "detail")
            case label:
                return ExtractionResult(
                    pillar=context.config.pillar,
                    entries=(ExtractedEntry(values={"item": label}, findings=()),),
                    usage=a_usage(PipelineStep.extraction),
                )


@pytest.mark.anyio
async def test_the_fast_tier_answers_when_it_can() -> None:
    script = TierScript(fast="fast", standard="standard")

    result = await AdaptiveExtractor(script).extract(TWO_EGGS)

    assert result.entries[0].values["item"] == "fast"
    assert script.asked == [ModelTier.fast]


@pytest.mark.anyio
async def test_an_answer_that_did_not_parse_escalates_to_standard() -> None:
    script = TierScript(fast=Unavailability.output_did_not_parse, standard="standard")

    result = await AdaptiveExtractor(script).extract(TWO_EGGS)

    assert result.entries[0].values["item"] == "standard"
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
            await AdaptiveExtractor(script).extract(TWO_EGGS)
        assert script.asked == [ModelTier.fast]


@pytest.mark.anyio
async def test_both_tiers_unparsed_is_a_refusal() -> None:
    script = TierScript(
        fast=Unavailability.output_did_not_parse, standard=Unavailability.output_did_not_parse
    )

    with pytest.raises(ModelUnavailableError):
        await AdaptiveExtractor(script).extract(TWO_EGGS)
    assert script.asked == [ModelTier.fast, ModelTier.standard]
