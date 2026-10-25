import re
from string import Formatter

import pytest

from farkad_ai.eval.example import GOLD, ExampleGold
from farkad_ai.eval.pillars import EXAMPLE_PILLARS
from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import ExtractionContext
from farkad_ai.pipeline.photo import photo_briefing
from farkad_ai.prompts import PromptAsset, list_prompts, prompt
from farkad_ai.routing.pass_one import routing_instructions
from tests.support import ScriptedModel, Tracked


def test_a_prompt_is_versioned_by_its_text() -> None:
    original = prompt("extraction")
    edited = PromptAsset(name=original.name, text=original.text + " Answer in metric.")

    assert edited.version != original.version
    assert original.version != prompt("pass_one").version
    assert len(original.version) == 12


@pytest.mark.anyio
async def test_a_pillar_s_extraction_version_moves_with_its_words_and_not_with_the_log() -> None:
    async def version_asked(pillar: Tracked, transcript: str) -> str:
        model = ScriptedModel({"entries": []})
        context = ExtractionContext(pillar=pillar, transcript=transcript, mentions=(transcript,))
        await PillarExtractor(model).extract(context)
        return model.asked[0].instructions_version

    water = Tracked("water")
    reworded = Tracked("water", guidance="Record each glass.")

    assert await version_asked(water, "a glass") == await version_asked(water, "two glasses")
    assert await version_asked(water, "a glass") != await version_asked(reworded, "a glass")


def test_every_brace_in_a_prompt_is_a_placeholder() -> None:
    for asset in list_prompts():
        for _, field, _, _ in Formatter().parse(asset.text):
            if field is None:
                continue
            assert field.isidentifier(), (
                f"{asset.name}.txt has a literal brace around {field!r}. "
                f"Write it as {{{{{field}}}}} if it is example text, not a placeholder."
            )


@pytest.mark.anyio
async def test_the_extraction_prompt_is_given_the_whole_log() -> None:
    model = ScriptedModel({"entries": []})
    context = ExtractionContext(
        pillar=Tracked("water"), transcript="a glass and an egg", mentions=("a glass",)
    )

    await PillarExtractor(model).extract(context)

    (asked,) = model.asked
    assert "a glass and an egg" in asked.instructions


def quoted(text: str) -> list[str]:
    return text.split('"')[1::2]


def test_no_prompt_or_worked_example_quotes_the_gold_set() -> None:
    gold = ExampleGold.model_validate_json(GOLD.read_text(encoding="utf-8"))
    said = [case.utterance.casefold() for case in gold.cases]
    illustrations = [
        *(phrase for asset in list_prompts() for phrase in quoted(asset.text)),
        *(quoted(pillar.examples)[0] for pillar in EXAMPLE_PILLARS),
    ]

    assert [each for each in illustrations if any(each.casefold() in s for s in said)] == []


def test_the_routing_prompt_gives_no_pillar_a_meaning_the_catalogue_did_not() -> None:
    told = set(re.findall(r"\w+", routing_instructions(()).casefold()))
    pillar_words = {
        word for pillar in EXAMPLE_PILLARS for word in (pillar.pillar, *pillar.title.split())
    }

    assert told & pillar_words == set()


def test_a_photo_is_read_in_the_language_the_consumer_names() -> None:
    assert "French" in photo_briefing("French")
