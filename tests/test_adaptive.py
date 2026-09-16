from __future__ import annotations

from decimal import Decimal

import pytest

from farkad_ai.extraction.adaptive import AdaptiveExtractor
from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    PillarExtractionPort,
)
from farkad_ai.types import PipelineStep, Usage


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


class FailingExtractor(PillarExtractionPort):
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        self.calls += 1
        raise ValueError("failed schema parsing")


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
async def test_adaptive_extractor_escalates_to_standard_on_failure() -> None:
    fast = FailingExtractor()
    standard = SuccessfulExtractor("standard")
    extractor = AdaptiveExtractor(fast, standard)
    ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

    res = await extractor.extract(ctx)
    assert res.entries[0]["item"] == "standard"
    assert fast.calls == 1
    assert standard.calls == 1


@pytest.mark.anyio
async def test_adaptive_extractor_raises_when_both_fail() -> None:
    fast = FailingExtractor()
    standard = FailingExtractor()
    extractor = AdaptiveExtractor(fast, standard)
    ctx = ExtractionContext(config=DummyPillarConfig(), transcript="two eggs")

    with pytest.raises(ValueError):
        await extractor.extract(ctx)
    assert fast.calls == 1
    assert standard.calls == 1
