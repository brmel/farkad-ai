from __future__ import annotations

import pytest

from farkad_ai.extraction.adaptive import AdaptiveExtractor
from farkad_ai.extraction.port import ExtractionContext
from farkad_ai.types import ModelUnavailableError, Unavailability
from tests.support import PillarConfig, RefusingExtractor, SuccessfulExtractor

TWO_EGGS = ExtractionContext(
    config=PillarConfig("food"), transcript="two eggs", mentions=("two eggs",)
)


@pytest.mark.anyio
async def test_adaptive_extractor_uses_fast_when_successful() -> None:
    fast = SuccessfulExtractor("fast")
    standard = SuccessfulExtractor("standard")
    extractor = AdaptiveExtractor(fast, standard)

    res = await extractor.extract(TWO_EGGS)
    assert res.entries[0]["item"] == "fast"
    assert fast.calls == 1
    assert standard.calls == 0


@pytest.mark.anyio
async def test_an_answer_that_did_not_parse_escalates_to_standard() -> None:
    fast = RefusingExtractor(Unavailability.output_did_not_parse)
    standard = SuccessfulExtractor("standard")
    extractor = AdaptiveExtractor(fast, standard)

    res = await extractor.extract(TWO_EGGS)
    assert res.entries[0]["item"] == "standard"
    assert fast.calls == 1
    assert standard.calls == 1


@pytest.mark.anyio
async def test_a_refusal_neither_tier_can_answer_is_never_paid_for_twice() -> None:
    for because in (Unavailability.provider_refused, Unavailability.usage_not_reported):
        fast = RefusingExtractor(because)
        standard = SuccessfulExtractor("standard")
        extractor = AdaptiveExtractor(fast, standard)

        with pytest.raises(ModelUnavailableError):
            await extractor.extract(TWO_EGGS)
        assert fast.calls == 1
        assert standard.calls == 0


@pytest.mark.anyio
async def test_adaptive_extractor_raises_when_both_tiers_cannot_parse() -> None:
    fast = RefusingExtractor(Unavailability.output_did_not_parse)
    standard = RefusingExtractor(Unavailability.output_did_not_parse)
    extractor = AdaptiveExtractor(fast, standard)

    with pytest.raises(ModelUnavailableError):
        await extractor.extract(TWO_EGGS)
    assert fast.calls == 1
    assert standard.calls == 1
