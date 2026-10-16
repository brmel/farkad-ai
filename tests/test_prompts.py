from pathlib import Path
from string import Formatter

import pytest

from farkad_ai.extraction.extractor import PillarExtractor
from farkad_ai.extraction.port import ExtractionContext
from farkad_ai.prompts import PromptAsset, list_prompts, prompt
from tests.support import ScriptedModel, Tracked


def test_a_prompt_is_versioned_by_its_text() -> None:
    original = prompt("extraction")
    edited = PromptAsset(name=original.name, text=original.text + " Answer in metric.")

    assert edited.version != original.version
    assert original.version != prompt("pass_one").version
    assert len(original.version) == 12


def test_a_consumer_loads_its_own_prompt_assets_the_same_way(tmp_path: Path) -> None:
    (tmp_path / "greeting.txt").write_text("  Hello {name}\n", encoding="utf-8")

    own = prompt("greeting", tmp_path)

    assert own == PromptAsset(name="greeting", text="Hello {name}")
    assert list_prompts(tmp_path) == (own,)


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
