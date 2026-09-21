from __future__ import annotations

from decimal import Decimal

import pytest

from farkad_ai.extraction.adaptive import AdaptiveExtractor
from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
)
from farkad_ai.types import (
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Unavailability,
    Usage,
)


class DummyPillarConfig:
    @property
    def pillar(self) -> str:
        return "food"


class SuccessfulExtractor(PillarExtractionPort):
    def __init__(self, label: str) -> None:
        self.label = label
        self.calls = 0

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        self.calls += 1
        return ExtractionResult(
            pillar=context.config.pillar,
            entries=({"item": self.label},),
            findings=(),
            usage=Usage(
                step=PipelineStep.extraction,
                model=f"model-{self.label}",
                prompt_version="v1",
                input_tokens=50,
                output_tokens=10,
                latency_ms=100,
                cost_cents=Decimal("0.01"),
            ),
        )


class RefusingExtractor(PillarExtractionPort):
    def __init__(self, because: Unavailability) -> None:
        self.because = because
        self.calls = 0

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        self.calls += 1
        raise ModelUnavailableError(ModelTier.fast, "model-fast", self.because, "detail")


@pytest.mark.anyio
async def test_adaptive_extractor_uses_fast_when_successful() -> None:
    fast = SuccessfulExtractor("fast")
    standard = SuccessfulExtractor("standard")
    extractor = AdaptiveExtractor(fast, standard)
    ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

    res = await extractor.extract(ctx)
    assert res.entries[0]["item"] == "fast"
    assert fast.calls == 1
    assert standard.calls == 0


@pytest.mark.anyio
async def test_an_answer_that_did_not_parse_escalates_to_standard() -> None:
    fast = RefusingExtractor(Unavailability.output_did_not_parse)
    standard = SuccessfulExtractor("standard")
    extractor = AdaptiveExtractor(fast, standard)
    ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

    res = await extractor.extract(ctx)
    assert res.entries[0]["item"] == "standard"
    assert fast.calls == 1
    assert standard.calls == 1


@pytest.mark.anyio
async def test_a_refusal_neither_tier_can_answer_is_never_paid_for_twice() -> None:
    for because in (Unavailability.provider_refused, Unavailability.usage_not_reported):
        fast = RefusingExtractor(because)
        standard = SuccessfulExtractor("standard")
        extractor = AdaptiveExtractor(fast, standard)
        ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

        with pytest.raises(ModelUnavailableError):
            await extractor.extract(ctx)
        assert fast.calls == 1
        assert standard.calls == 0


@pytest.mark.anyio
async def test_adaptive_extractor_raises_when_both_tiers_cannot_parse() -> None:
    fast = RefusingExtractor(Unavailability.output_did_not_parse)
    standard = RefusingExtractor(Unavailability.output_did_not_parse)
    extractor = AdaptiveExtractor(fast, standard)
    ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

    with pytest.raises(ModelUnavailableError):
        await extractor.extract(ctx)
    assert fast.calls == 1
    assert standard.calls == 1
