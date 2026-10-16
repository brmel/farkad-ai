import pytest

from farkad_ai.examples import EXAMPLE_PILLARS, ExamplePillar
from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import ExtractionContext, ExtractionResult
from tests.support import ScriptedModel


def example(pillar: str) -> ExamplePillar:
    return next(each for each in EXAMPLE_PILLARS if each.pillar == pillar)


async def extracted(pillar: str, *answered: dict[str, object]) -> ExtractionResult:
    model = ScriptedModel({"entries": list(answered)})
    context = ExtractionContext(pillar=example(pillar), transcript="said", mentions=("said",))
    return await PillarExtractor(model).extract(context)


@pytest.mark.anyio
async def test_an_entry_naming_only_its_category_is_kept_and_one_naming_nothing_is_dropped() -> (
    None
):
    coffee = await extracted("water", {"category": "coffee"})
    nothing = await extracted("food", {})

    assert [entry.values["category"] for entry in coffee.entries] == ["coffee"]
    assert nothing.entries == ()
